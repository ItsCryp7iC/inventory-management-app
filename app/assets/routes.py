from flask import render_template, redirect, url_for, flash, request
from . import bp
from app.extensions import db
from app.models import Asset, Location, Category, SubCategory, Vendor, AssetEvent
from .forms import AssetForm
from datetime import date



def _populate_form_choices(form: AssetForm):
    """Populate dropdown choices for the asset form."""
    locations = Location.query.order_by(Location.name).all()
    categories = Category.query.order_by(Category.name).all()
    subcategories = SubCategory.query.order_by(SubCategory.name).all()
    vendors = Vendor.query.order_by(Vendor.name).all()

    form.location_id.choices = [(0, "--- Select ---")] + [
        (loc.id, loc.name) for loc in locations
    ]
    form.category_id.choices = [(0, "--- Select ---")] + [
        (cat.id, cat.name) for cat in categories
    ]
    form.subcategory_id.choices = [(0, "--- Select ---")] + [
        (sc.id, f"{sc.category.name} - {sc.name}") for sc in subcategories
    ]
    form.vendor_id.choices = [(0, "--- Select ---")] + [
        (v.id, v.name) for v in vendors
    ]


def _normalize_id(value):
    return value if value and value != 0 else None

def log_asset_event(
    asset: Asset,
    event_type: str,
    note: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    from_location_id: int | None = None,
    to_location_id: int | None = None,
):
    event = AssetEvent(
        asset_id=asset.id,
        event_type=event_type,
        note=note,
        from_status=from_status,
        to_status=to_status,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
    )
    db.session.add(event)
    # Do NOT commit here – caller will commit transaction


@bp.route("/")
def list_assets():
    status = request.args.get("status", "").strip()
    location_id = request.args.get("location_id", "").strip()
    q = request.args.get("q", "").strip()

    query = Asset.query

    if status:
        query = query.filter(Asset.status == status)

    if location_id and location_id.isdigit():
        query = query.filter(Asset.location_id == int(location_id))

    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Asset.name.ilike(like_pattern),
                Asset.asset_tag.ilike(like_pattern),
                Asset.serial_number.ilike(like_pattern),
            )
        )

    assets = query.order_by(Asset.id.desc()).all()

    # For filter dropdowns
    locations = Location.query.order_by(Location.name).all()

    status_choices = [
        ("", "All statuses"),
        ("in_use", "In Use"),
        ("in_stock", "In Stock"),
        ("under_repair", "Under Repair"),
        ("retired", "Retired"),
        ("disposed", "Disposed"),
    ]

    return render_template(
        "assets/list.html",
        assets=assets,
        status=status,
        location_id=location_id,
        q=q,
        locations=locations,
        status_choices=status_choices,
    )


@bp.route("/new", methods=["GET", "POST"])
def create_asset():
    form = AssetForm()
    _populate_form_choices(form)

    # Default status / location logic you already had...
    # (leave that part as-is)

    if form.validate_on_submit():
        asset = Asset(
            asset_tag=form.asset_tag.data or None,
            name=form.name.data,
            description=form.description.data or None,
            serial_number=form.serial_number.data or None,
            status=form.status.data,
            purchase_date=form.purchase_date.data,
            warranty_expiry_date=form.warranty_expiry_date.data,
            cost=form.cost.data,
            category_id=_normalize_id(form.category_id.data),
            subcategory_id=_normalize_id(form.subcategory_id.data),
            location_id=_normalize_id(form.location_id.data),
            vendor_id=_normalize_id(form.vendor_id.data),
            notes=form.notes.data or None,
        )

        db.session.add(asset)
        db.session.flush()  # ensure asset.id exists before logging

        log_asset_event(
            asset=asset,
            event_type="created",
            note="Asset created",
            to_status=asset.status,
            to_location_id=asset.location_id,
        )

        db.session.commit()
        flash("Asset created successfully.", "success")
        return redirect(url_for("assets.list_assets"))

    if form.errors:
        flash("Please correct the errors in the form.", "danger")

    return render_template("assets/create.html", form=form)


@bp.route("/<int:asset_id>/edit", methods=["GET", "POST"])
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    form = AssetForm(obj=asset)
    _populate_form_choices(form)

    if form.validate_on_submit():
        asset.asset_tag = form.asset_tag.data or None
        asset.name = form.name.data
        asset.description = form.description.data or None
        asset.serial_number = form.serial_number.data or None
        asset.status = form.status.data

        # dropdowns
        asset.category_id = _normalize_id(form.category_id.data)
        asset.subcategory_id = _normalize_id(form.subcategory_id.data)
        asset.location_id = _normalize_id(form.location_id.data)
        asset.vendor_id = _normalize_id(form.vendor_id.data)

        # dates / cost
        asset.purchase_date = form.purchase_date.data
        asset.warranty_expiry_date = form.warranty_expiry_date.data
        asset.cost = form.cost.data

        # notes
        asset.notes = form.notes.data or None

        db.session.commit()
        flash("Asset updated successfully.", "success")
        return redirect(url_for("assets.list_assets"))

    if form.errors and request.method == "POST":
        flash("Please correct the errors in the form.", "danger")

    return render_template(
        "assets/create.html",
        form=form,
        is_edit=True,
        asset=asset
    )




@bp.route("/<int:asset_id>")
def asset_detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    events = (
        AssetEvent.query
        .filter_by(asset_id=asset.id)
        .order_by(AssetEvent.created_at.desc())
        .all()
    )
    return render_template("assets/detail.html", asset=asset, events=events)

    form = AssetForm(obj=asset)
    _populate_form_choices(form)

    # For GET, AssetForm(obj=asset) already pre-fills everything.
    # For POST, WTForms will override with submitted data.

    if form.validate_on_submit():
        asset.asset_tag = form.asset_tag.data or None
        asset.name = form.name.data
        asset.description = form.description.data or None
        asset.serial_number = form.serial_number.data or None
        asset.status = form.status.data
        asset.purchase_date = form.purchase_date.data
        asset.warranty_expiry_date = form.warranty_expiry_date.data
        asset.cost = form.cost.data
        asset.category_id = _normalize_id(form.category_id.data)
        asset.subcategory_id = _normalize_id(form.subcategory_id.data)
        asset.location_id = _normalize_id(form.location_id.data)
        asset.vendor_id = _normalize_id(form.vendor_id.data)
        asset.notes = form.notes.data or None

        db.session.commit()
        flash("Asset updated successfully.", "success")
        return redirect(url_for("assets.list_assets"))

    if form.errors and request.method == "POST":
        flash("Please correct the errors in the form.", "danger")

@bp.route("/<int:asset_id>/retire", methods=["POST"])
def retire_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    if asset.status in ["retired", "disposed"]:
        flash("Asset is already retired or disposed.", "warning")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    old_status = asset.status
    old_location_id = asset.location_id

    asset.status = "retired"

    log_asset_event(
        asset=asset,
        event_type="retire",
        note="Asset marked as retired",
        from_status=old_status,
        to_status=asset.status,
        from_location_id=old_location_id,
        to_location_id=asset.location_id,
    )

    db.session.commit()
    flash("Asset has been marked as retired.", "success")
    return redirect(url_for("assets.asset_detail", asset_id=asset.id))


@bp.route("/<int:asset_id>/dispose", methods=["POST"])
def dispose_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    if asset.status == "disposed":
        flash("Asset is already disposed.", "warning")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    old_status = asset.status
    old_location_id = asset.location_id

    asset.status = "disposed"

    log_asset_event(
        asset=asset,
        event_type="dispose",
        note="Asset marked as disposed",
        from_status=old_status,
        to_status=asset.status,
        from_location_id=old_location_id,
        to_location_id=asset.location_id,
    )

    db.session.commit()
    flash("Asset has been marked as disposed.", "success")
    return redirect(url_for("assets.asset_detail", asset_id=asset.id))



@bp.route("/<int:asset_id>/assign", methods=["POST"])
def assign_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    if asset.status in ["retired", "disposed"]:
        flash("Cannot assign a retired or disposed asset.", "danger")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    assigned_to = request.form.get("assigned_to", "").strip()
    assigned_department = request.form.get("assigned_department", "").strip()
    assigned_email = request.form.get("assigned_email", "").strip()

    if not assigned_to:
        flash("Assignee name is required to assign an asset.", "danger")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    old_status = asset.status
    old_location_id = asset.location_id

    asset.assigned_to = assigned_to
    asset.assigned_department = assigned_department or None
    asset.assigned_email = assigned_email or None
    asset.assigned_at = date.today()

    if asset.status in ["in_stock", "under_repair"]:
        asset.status = "in_use"

    # log event
    note_parts = [f"Assigned to {assigned_to}"]
    if assigned_department:
        note_parts.append(f"({assigned_department})")
    if assigned_email:
        note_parts.append(f"<{assigned_email}>")

    log_asset_event(
        asset=asset,
        event_type="assign",
        note=" ".join(note_parts),
        from_status=old_status,
        to_status=asset.status,
        from_location_id=old_location_id,
        to_location_id=asset.location_id,
    )

    db.session.commit()
    flash("Asset has been assigned successfully.", "success")
    return redirect(url_for("assets.asset_detail", asset_id=asset.id))



@bp.route("/<int:asset_id>/unassign", methods=["POST"])
def unassign_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    if not asset.assigned_to and not asset.assigned_at:
        flash("This asset is not currently assigned.", "warning")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    old_status = asset.status
    old_location_id = asset.location_id
    previous_assignee = asset.assigned_to

    asset.assigned_to = None
    asset.assigned_department = None
    asset.assigned_email = None
    asset.assigned_at = None

    if asset.status == "in_use":
        asset.status = "in_stock"

    log_asset_event(
        asset=asset,
        event_type="unassign",
        note=f"Unassigned from {previous_assignee}" if previous_assignee else "Unassigned",
        from_status=old_status,
        to_status=asset.status,
        from_location_id=old_location_id,
        to_location_id=asset.location_id,
    )

    db.session.commit()
    flash("Asset has been unassigned and returned to stock.", "success")
    return redirect(url_for("assets.asset_detail", asset_id=asset.id))
