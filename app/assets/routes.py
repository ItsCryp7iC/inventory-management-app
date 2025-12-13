from __future__ import annotations

from datetime import date, datetime
import io
import csv
from decimal import Decimal
from typing import Optional

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from . import bp
from .forms import AssetForm
from app.extensions import db
from app.models import Asset, Location, Category, SubCategory, Vendor, AssetEvent, AssetTagSequence
from app.auth.decorators import admin_required


# ----------------------------
# Helpers
# ----------------------------

def _max_existing_seq_for_office_year(office_code: str, year: int) -> int:
    """
    Scan existing asset tags to find the max sequence for an office/year.
    This is used to initialize/repair the counter when the sequence table is
    created after assets already exist.
    """
    company_prefix = "ESS"
    year_str = str(year)
    max_seq = 0

    # pattern: ESS-{office}-{category}-{year}-{seq}
    pattern = f"{company_prefix}-{office_code}-%-{year_str}-%"
    tags = (
        Asset.query
        .with_entities(Asset.asset_tag)
        .filter(Asset.asset_tag.like(pattern))
        .all()
    )
    for (tag,) in tags:
        parts = (tag or "").split("-")
        if len(parts) < 5:
            continue
        # quick sanity: ESS, office, cat, year, seq
        if parts[0] != company_prefix or parts[1] != office_code or parts[-2] != year_str:
            continue
        try:
            seq_val = int(parts[-1])
            if seq_val > max_seq:
                max_seq = seq_val
        except ValueError:
            continue
    return max_seq


def _normalize_id(value):
    """Convert '0' / 0 / empty to None, keep valid int values."""
    return value if value and value != 0 else None


def _populate_form_choices(form: AssetForm):
    """Populate dropdown choices for the asset form."""
    locations = Location.query.order_by(Location.name).all()
    categories = Category.query.order_by(Category.name).all()
    subcategories = SubCategory.query.order_by(SubCategory.name).all()
    vendors = Vendor.query.order_by(Vendor.name).all()

    form.location_id.choices = [(0, "--- Select ---")] + [(loc.id, loc.name) for loc in locations]
    form.category_id.choices = [(0, "--- Select ---")] + [(cat.id, cat.name) for cat in categories]
    form.subcategory_id.choices = [(0, "--- Select ---")] + [
        (sc.id, f"{sc.category.name} - {sc.name}") for sc in subcategories
    ]
    form.vendor_id.choices = [(0, "--- Select ---")] + [(v.id, v.name) for v in vendors]


def _get_or_create_sequence(office_code: str, year: int) -> AssetTagSequence:
    """
    Fetch or create the sequence tracker for an office/year.
    Uses with_for_update to reduce race conditions on DBs that support it.
    """
    from sqlalchemy.exc import OperationalError

    seq = None
    try:
        seq = (
            AssetTagSequence.query
            .filter_by(office_code=office_code, year=year)
            .with_for_update()
            .first()
        )
    except OperationalError as exc:
        # Fallback for missing table (e.g., migration not applied yet)
        if "no such table" in str(exc).lower() and "asset_tag_sequences" in str(exc).lower():
            db.session.rollback()
            db.create_all()
            seq = (
                AssetTagSequence.query
                .filter_by(office_code=office_code, year=year)
                .with_for_update()
                .first()
            )
        else:
            raise

    if not seq:
        seq = AssetTagSequence(office_code=office_code, year=year, last_seq=0)
        db.session.add(seq)
        # Initialize from existing tags if any were created before this table existed
        existing_max = _max_existing_seq_for_office_year(office_code, year)
        if existing_max > 0:
            seq.last_seq = existing_max
        db.session.flush()
    else:
        # Repair in case the stored last_seq lags behind real tags
        existing_max = _max_existing_seq_for_office_year(office_code, year)
        if existing_max > seq.last_seq:
            seq.last_seq = existing_max
            db.session.flush()
    return seq


def generate_asset_tag(location: Location, category: Category, year: int) -> str:
    """
    Format:
      ESS-{OfficeCode}-{CategoryCode}-{Year}-{0001}

    Example:
      ESS-M-COMP-2025-0001

    Sequencing rule: sequence is per Office+Year (shared across all categories
    for that office/year) and never reuses numbers even if assets are deleted.
    """
    company = "ESS"

    office_code = (location.code or "").strip().upper()
    cat_code = (category.code or "").strip().upper()

    if not office_code:
        raise ValueError("Location.code missing (expected M/P).")
    if not cat_code:
        raise ValueError("Category.code missing (expected COMP/MONI etc.).")

    seq = _get_or_create_sequence(office_code, year)
    next_seq = seq.last_seq + 1
    seq.last_seq = next_seq

    year_str = str(year)
    return f"{company}-{office_code}-{cat_code}-{year_str}-{next_seq:04d}"


def ensure_vendor_code(vendor: Vendor):
    """
    Ensure a vendor has a code; auto-generate if missing.
    """
    if not vendor or vendor.code:
        return

    existing_codes = Vendor.query.with_entities(Vendor.code).filter(Vendor.code.isnot(None)).all()
    max_num = 0
    for (code,) in existing_codes:
        if not code:
            continue
        code_upper = code.upper().strip()
        if code_upper.startswith("V") and code_upper[1:].isdigit():
            max_num = max(max_num, int(code_upper[1:]))

    vendor.code = f"V{max_num + 1:03d}"
    db.session.commit()

def _next_vendor_code_value():
    """
    Compute the next vendor code (V###) without committing or mutating records.
    """
    existing_codes = Vendor.query.with_entities(Vendor.code).filter(Vendor.code.isnot(None)).all()
    max_num = 0
    for (code,) in existing_codes:
        if not code:
            continue
        code_upper = code.upper().strip()
        if code_upper.startswith("V") and code_upper[1:].isdigit():
            try:
                max_num = max(max_num, int(code_upper[1:]))
            except ValueError:
                continue
    return f"V{max_num + 1:03d}"


def log_asset_event(
    asset: Asset,
    event_type: str,
    note: Optional[str] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    from_location_id: Optional[int] = None,
    to_location_id: Optional[int] = None,
):
    """
    Add an AssetEvent row. Caller commits.
    """
    ev = AssetEvent(
        asset_id=asset.id,
        event_type=event_type,
        note=note,
        from_status=from_status,
        to_status=to_status,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        performed_by_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(ev)


# ----------------------------
# Routes
# ----------------------------

@bp.route("/")
@login_required
def list_assets():
    status = request.args.get("status", "").strip()
    location_id = request.args.get("location_id", "").strip()
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "id").strip()
    direction = request.args.get("dir", "desc").strip().lower()
    export = request.args.get("export", "").strip()

    query = (
        Asset.query
        .outerjoin(Category, Asset.category_id == Category.id)
        .outerjoin(SubCategory, Asset.subcategory_id == SubCategory.id)
        .outerjoin(Location, Asset.location_id == Location.id)
    )

    if status:
        if status == "assigned":
            query = query.filter(Asset.status.in_(["assigned", "in_use"]))
        else:
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

    sort_map = {
        "id": Asset.id,
        "asset_tag": Asset.asset_tag,
        "name": Asset.name,
        "status": Asset.status,
        "purchase_date": Asset.purchase_date,
        "warranty_expiry_date": Asset.warranty_expiry_date,
        "category": Category.name,
        "subcategory": SubCategory.name,
        "location": Location.name,
        "created_at": Asset.created_at,
    }

    sort_col = sort_map.get(sort, Asset.id)
    sort_func = sort_col.desc if direction == "desc" else sort_col.asc
    assets = query.order_by(sort_func()).all()

    # Handle export toggle quickly (admin only)
    if export == "csv":
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return export_assets_csv(assets)

    locations = Location.query.order_by(Location.name).all()
    status_choices = [
        ("", "All statuses"),
        ("in_stock", "In Stock"),
        ("assigned", "Assigned"),
        ("repair", "Repair"),
        ("damaged", "Damaged"),
        ("missing", "Missing"),
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
        sort=sort,
        direction=direction,
    )


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create_asset():
    form = AssetForm()
    _populate_form_choices(form)

    if form.validate_on_submit():
        # We must have Location + Category to generate tag
        location_id = _normalize_id(form.location_id.data)
        category_id = _normalize_id(form.category_id.data)

        location = Location.query.get(location_id) if location_id else None
        category = Category.query.get(category_id) if category_id else None

        if not location or not category:
            flash("Location and Category are required to generate Asset Tag.", "danger")
            return render_template("assets/create.html", form=form)

        try:
            asset_tag = generate_asset_tag(location, category, date.today().year)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("assets/create.html", form=form)

        asset = Asset(
            asset_tag=asset_tag,
            name=form.name.data,
            description=form.description.data or None,
            serial_number=form.serial_number.data or None,
            status=form.status.data,
            purchase_date=form.purchase_date.data,
            warranty_expiry_date=form.warranty_expiry_date.data,
            cost=form.cost.data,
            category_id=category_id,
            subcategory_id=_normalize_id(form.subcategory_id.data),
            location_id=location_id,
            vendor_id=_normalize_id(form.vendor_id.data),
            notes=form.notes.data or None,
        )

        db.session.add(asset)
        db.session.flush()  # ensure asset.id exists

        log_asset_event(
            asset=asset,
            event_type="created",
            note=f"Asset created ({asset.asset_tag})",
            to_status=asset.status,
            to_location_id=asset.location_id,
        )

        db.session.commit()
        flash(f"Asset created successfully: {asset.asset_tag}", "success")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    if form.errors:
        flash("Please correct the errors in the form.", "danger")

    return render_template("assets/create.html", form=form)


@bp.route("/<int:asset_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    form = AssetForm(obj=asset)
    _populate_form_choices(form)

    if form.validate_on_submit():
        # asset_tag is intentionally IMMUTABLE (auto-generated)
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
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    if form.errors and request.method == "POST":
        flash("Please correct the errors in the form.", "danger")

    return render_template("assets/create.html", form=form, is_edit=True, asset=asset)


@bp.route("/<int:asset_id>")
@login_required
def asset_detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    ensure_vendor_code(asset.vendor)
    events = (
        AssetEvent.query
        .filter_by(asset_id=asset.id)
        .order_by(AssetEvent.created_at.desc())
        .all()
    )
    return render_template("assets/detail.html", asset=asset, events=events)


@bp.route("/<int:asset_id>/retire", methods=["POST"])
@admin_required
def retire_asset(asset_id):
    flash("The 'Retired' status is no longer used.", "warning")
    return redirect(url_for("assets.asset_detail", asset_id=asset_id))


@bp.route("/<int:asset_id>/dispose", methods=["POST"])
@admin_required
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
@admin_required
def assign_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    if asset.status in ["disposed", "repair", "missing", "damaged"]:
        flash("Cannot assign an asset that is disposed, under repair, missing, or damaged.", "danger")
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

    if asset.status in ["in_stock", "in_use"]:
        asset.status = "assigned"

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
@admin_required
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

    if asset.status in ["assigned", "in_use"]:
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


@bp.route("/<int:asset_id>/repair/start", methods=["GET", "POST"])
@admin_required
def start_repair(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    vendors = Vendor.query.order_by(Vendor.name.asc()).all()

    if asset.status in ["disposed", "missing"]:
        flash("Cannot send a disposed or missing asset to repair.", "danger")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    if asset.status == "repair":
        flash("Asset is already under repair.", "warning")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    if request.method == "POST":
        vendor_option = request.form.get("vendor_option", "asset_vendor")
        repair_vendor = request.form.get("repair_vendor", "").strip()
        repair_vendor_phone = request.form.get("repair_vendor_phone", "").strip()
        repair_vendor_address = request.form.get("repair_vendor_address", "").strip()
        repair_reference = request.form.get("repair_reference", "").strip()
        repair_notes = request.form.get("repair_notes", "").strip()

        # Resolve vendor choice (existing vs new)
        resolved_vendor_name = None
        resolved_vendor_phone = None
        resolved_vendor_address = None
        chosen_vendor = None

        # If using asset vendor and it exists, prefer that record
        if vendor_option == "asset_vendor" and asset.vendor:
            chosen_vendor = asset.vendor
        elif repair_vendor:
            # Look up by name (case-insensitive) when user typed/selected a vendor
            chosen_vendor = (
                Vendor.query
                .filter(func.lower(Vendor.name) == repair_vendor.lower())
                .first()
            )

        if chosen_vendor:
            resolved_vendor_name = chosen_vendor.name
            resolved_vendor_phone = chosen_vendor.contact_phone or repair_vendor_phone or None
            resolved_vendor_address = chosen_vendor.address or repair_vendor_address or None
        else:
            # New vendor path — require a name
            if not repair_vendor:
                flash("Please provide a repair vendor or service center.", "danger")
                return redirect(url_for("assets.start_repair", asset_id=asset.id))

            # Require contact details for new vendors so they are useful later
            if not repair_vendor_phone or not repair_vendor_address:
                flash("Please add vendor number and address for a new repair vendor.", "danger")
                return redirect(url_for("assets.start_repair", asset_id=asset.id))

            new_vendor = Vendor(
                name=repair_vendor,
                contact_phone=repair_vendor_phone,
                address=repair_vendor_address,
            )
            new_vendor.code = _next_vendor_code_value()
            db.session.add(new_vendor)

            resolved_vendor_name = new_vendor.name
            resolved_vendor_phone = new_vendor.contact_phone
            resolved_vendor_address = new_vendor.address

        old_status = asset.status
        old_location_id = asset.location_id

        asset.repair_opened_at = date.today()
        asset.repair_vendor = resolved_vendor_name or None
        asset.repair_vendor_phone = resolved_vendor_phone or None
        asset.repair_vendor_address = resolved_vendor_address or None
        asset.repair_reference = repair_reference or None
        asset.repair_notes = repair_notes or None

        asset.status = "repair"

        # Clear assignment when going to repair
        if asset.assigned_to:
            asset.assigned_to = None
            asset.assigned_department = None
            asset.assigned_email = None
            asset.assigned_at = None

        note_parts = ["Sent to repair"]
        if resolved_vendor_name:
            note_parts.append(f"Vendor: {resolved_vendor_name}")
        if resolved_vendor_phone:
            note_parts.append(f"Phone: {resolved_vendor_phone}")
        if resolved_vendor_address:
            note_parts.append(f"Address: {resolved_vendor_address}")
        if repair_reference:
            note_parts.append(f"Ref: {repair_reference}")
        if repair_notes:
            note_parts.append(f"Notes: {repair_notes}")

        log_asset_event(
            asset=asset,
            event_type="repair_start",
            note=" | ".join(note_parts),
            from_status=old_status,
            to_status=asset.status,
            from_location_id=old_location_id,
            to_location_id=asset.location_id,
        )

        db.session.commit()
        flash("Asset marked as under repair.", "success")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    return render_template("assets/repair_start.html", asset=asset, vendors=vendors)


@bp.route("/<int:asset_id>/repair/complete", methods=["GET", "POST"])
@admin_required
def complete_repair(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    if asset.status != "repair":
        flash("This asset is not currently under repair.", "warning")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    if request.method == "POST":
        outcome = request.form.get("outcome", "").strip()  # "back_to_stock" or "disposed"
        repair_cost = request.form.get("repair_cost", "").strip()
        repair_notes = request.form.get("repair_notes", "").strip()

        old_status = asset.status
        old_location_id = asset.location_id

        cost_value = None
        if repair_cost:
            try:
                cost_value = float(repair_cost)
            except ValueError:
                flash("Repair cost must be a number.", "danger")
                return redirect(url_for("assets.complete_repair", asset_id=asset.id))

        asset.repair_closed_at = date.today()
        if cost_value is not None:
            asset.repair_cost = cost_value
        if repair_notes:
            asset.repair_notes = repair_notes

        asset.status = "disposed" if outcome == "disposed" else "in_stock"

        note_parts = ["Repair completed"]
        note_parts.append("Outcome: Asset disposed after repair" if outcome == "disposed" else "Outcome: Returned to stock")
        if repair_cost:
            note_parts.append(f"Cost: {repair_cost}")
        if repair_notes:
            note_parts.append(f"Notes: {repair_notes}")

        log_asset_event(
            asset=asset,
            event_type="repair_end",
            note=" | ".join(note_parts),
            from_status=old_status,
            to_status=asset.status,
            from_location_id=old_location_id,
            to_location_id=asset.location_id,
        )

        db.session.commit()
        flash("Repair completed and status updated.", "success")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    return render_template("assets/repair_complete.html", asset=asset)


@bp.route("/<int:asset_id>/move", methods=["GET", "POST"])
@admin_required
def move_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    locations = Location.query.order_by(Location.name).all()

    if request.method == "POST":
        new_location_id = request.form.get("new_location_id", "").strip()
        reason = request.form.get("reason", "").strip()
        reference = request.form.get("reference", "").strip()

        if not new_location_id.isdigit():
            flash("Please select a valid location.", "danger")
            return redirect(url_for("assets.move_asset", asset_id=asset.id))

        new_location_id_int = int(new_location_id)

        if new_location_id_int == asset.location_id:
            flash("Asset is already in this location.", "warning")
            return redirect(url_for("assets.move_asset", asset_id=asset.id))

        old_location_id = asset.location_id
        asset.location_id = new_location_id_int

        note_parts = [f"Moved from LocationID {old_location_id} to {new_location_id_int}"]
        if reason:
            note_parts.append(f"Reason: {reason}")
        if reference:
            note_parts.append(f"Ref: {reference}")

        log_asset_event(
            asset=asset,
            event_type="move",
            note=" | ".join(note_parts),
            from_location_id=old_location_id,
            to_location_id=new_location_id_int,
            from_status=asset.status,
            to_status=asset.status,
        )

        db.session.commit()
        flash("Asset moved successfully.", "success")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    return render_template("assets/move.html", asset=asset, locations=locations)


@bp.route("/<int:asset_id>/delete", methods=["POST"])
@admin_required
def delete_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    asset_label = asset.asset_tag or asset.name

    db.session.delete(asset)
    db.session.commit()
    flash(f"Asset {asset_label} has been deleted.", "success")
    return redirect(url_for("assets.list_assets"))


@bp.route("/<int:asset_id>/mark-damaged", methods=["POST"])
@admin_required
def mark_damaged(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    old_status = asset.status

    if asset.status == "disposed":
        flash("Disposed assets cannot be marked as damaged.", "danger")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    asset.status = "damaged"

    log_asset_event(
        asset=asset,
        event_type="damaged",
        note="Asset marked as damaged.",
        from_status=old_status,
        to_status=asset.status,
        from_location_id=asset.location_id,
        to_location_id=asset.location_id,
    )

    db.session.commit()
    flash("Asset marked as damaged.", "success")
    return redirect(url_for("assets.asset_detail", asset_id=asset.id))


@bp.route("/<int:asset_id>/mark-missing", methods=["POST"])
@admin_required
def mark_missing(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    old_status = asset.status

    if asset.status == "disposed":
        flash("Disposed assets cannot be marked as missing.", "danger")
        return redirect(url_for("assets.asset_detail", asset_id=asset.id))

    asset.status = "missing"

    log_asset_event(
        asset=asset,
        event_type="missing",
        note="Asset marked as missing.",
        from_status=old_status,
        to_status=asset.status,
        from_location_id=asset.location_id,
        to_location_id=asset.location_id,
    )

    db.session.commit()
    flash("Asset marked as missing.", "success")
    return redirect(url_for("assets.asset_detail", asset_id=asset.id))


# ----------------------------
# CSV Export / Import
# ----------------------------

EXPORT_HEADERS = [
    "asset_tag",
    "name",
    "status",
    "category_code",
    "subcategory_name",
    "location_code",
    "vendor_name",
    "serial_number",
    "purchase_date",
    "warranty_expiry_date",
    "cost",
    "description",
    "notes",
]

ALLOWED_STATUSES = {"in_stock", "assigned", "repair", "damaged", "missing", "disposed", "in_use"}  # include legacy in_use


@admin_required
def export_assets_csv(assets):
    """Return a CSV response for the given assets list."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(EXPORT_HEADERS)

    for a in assets:
        writer.writerow([
            a.asset_tag or "",
            a.name or "",
            a.status or "",
            a.category.code if a.category else "",
            a.subcategory.name if a.subcategory else "",
            a.location.code if a.location else "",
            a.vendor.name if a.vendor else "",
            a.serial_number or "",
            a.purchase_date or "",
            a.warranty_expiry_date or "",
            a.cost or "",
            (a.description or "").replace("\n", " ").strip(),
            (a.notes or "").replace("\n", " ").strip(),
        ])

    csv_data = output.getvalue()
    output.close()

    from flask import Response
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=assets_export.csv"
        }
    )


@bp.route("/import", methods=["GET", "POST"])
@admin_required
def import_assets():
    if request.method == "GET":
        return redirect(url_for("settings.general_settings"))

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Please upload a CSV file.", "danger")
            return redirect(url_for("assets.import_assets"))

        try:
            content = file.read().decode("utf-8-sig")
        except Exception:
            flash("Could not read the uploaded file. Ensure it is valid UTF-8.", "danger")
            return redirect(url_for("assets.import_assets"))

        reader = csv.DictReader(io.StringIO(content))
        missing_headers = [h for h in ["name", "status", "category_code", "location_code"] if h not in reader.fieldnames]
        if missing_headers:
            flash(f"Missing required headers: {', '.join(missing_headers)}", "danger")
            return redirect(url_for("assets.import_assets"))

        created = 0
        errors = []
        row_num = 1  # header

        for row in reader:
            row_num += 1
            name = (row.get("name") or "").strip()
            status = (row.get("status") or "").strip().lower() or "in_stock"
            if status == "in_use":
                status = "assigned"
            category_code = (row.get("category_code") or "").strip().upper()
            subcategory_name = (row.get("subcategory_name") or "").strip()
            location_code = (row.get("location_code") or "").strip().upper()
            vendor_name = (row.get("vendor_name") or "").strip()
            asset_tag = (row.get("asset_tag") or "").strip()
            serial_number = (row.get("serial_number") or "").strip()
            purchase_date_raw = (row.get("purchase_date") or "").strip()
            warranty_date_raw = (row.get("warranty_expiry_date") or "").strip()
            cost_raw = (row.get("cost") or "").strip()
            description = (row.get("description") or "").strip()
            notes = (row.get("notes") or "").strip()

            if not name:
                errors.append(f"Row {row_num}: name is required.")
                continue

            if status not in ALLOWED_STATUSES:
                errors.append(f"Row {row_num}: invalid status '{status}'.")
                continue

            if not category_code:
                errors.append(f"Row {row_num}: category_code is required.")
                continue

            if not location_code:
                errors.append(f"Row {row_num}: location_code is required.")
                continue

            category = Category.query.filter_by(code=category_code).first()
            if not category:
                errors.append(f"Row {row_num}: category code '{category_code}' not found.")
                continue

            location = Location.query.filter_by(code=location_code).first()
            if not location:
                errors.append(f"Row {row_num}: location code '{location_code}' not found.")
                continue

            subcategory = None
            if subcategory_name:
                subcategory = (
                    SubCategory.query
                    .filter(SubCategory.name == subcategory_name, SubCategory.category_id == category.id)
                    .first()
                )
                if not subcategory:
                    errors.append(f"Row {row_num}: subcategory '{subcategory_name}' not found under category '{category_code}'.")
                    continue

            vendor = None
            if vendor_name:
                vendor = Vendor.query.filter_by(name=vendor_name).first()
                if not vendor:
                    vendor = Vendor(name=vendor_name)
                    db.session.add(vendor)
                    db.session.flush()

            # Dates
            def parse_date(val, label):
                if not val:
                    return None
                try:
                    return datetime.strptime(val, "%Y-%m-%d").date()
                except ValueError:
                    errors.append(f"Row {row_num}: {label} must be YYYY-MM-DD.")
                    return None

            purchase_date = parse_date(purchase_date_raw, "purchase_date")
            warranty_date = parse_date(warranty_date_raw, "warranty_expiry_date")

            if any(err.startswith(f"Row {row_num}:") for err in errors):
                continue

            # Cost
            cost_val = None
            if cost_raw:
                try:
                    cost_val = Decimal(cost_raw)
                except Exception:
                    errors.append(f"Row {row_num}: cost must be a number.")
                    continue

            # Asset tag
            if asset_tag:
                existing = Asset.query.filter_by(asset_tag=asset_tag).first()
                if existing:
                    errors.append(f"Row {row_num}: asset_tag '{asset_tag}' already exists.")
                    continue
            else:
                try:
                    asset_tag = generate_asset_tag(location, category, date.today().year)
                except Exception as exc:
                    errors.append(f"Row {row_num}: could not generate tag ({exc}).")
                    continue

            asset = Asset(
                asset_tag=asset_tag,
                name=name,
                status=status,
                category_id=category.id,
                subcategory_id=subcategory.id if subcategory else None,
                location_id=location.id,
                vendor_id=vendor.id if vendor else None,
                serial_number=serial_number or None,
                purchase_date=purchase_date,
                warranty_expiry_date=warranty_date,
                cost=cost_val,
                description=description or None,
                notes=notes or None,
            )
            db.session.add(asset)
            db.session.flush()

            log_asset_event(
                asset=asset,
                event_type="created",
                note="Asset imported via CSV",
                to_status=asset.status,
                to_location_id=asset.location_id,
            )

            created += 1

        if errors:
            db.session.rollback()
            for err in errors:
                flash(err, "danger")
            if created:
                flash(f"{created} assets were created before errors occurred; nothing was saved. Fix errors and try again.", "warning")
            return redirect(url_for("assets.import_assets"))

        db.session.commit()
        flash(f"Imported {created} assets successfully.", "success")
        return redirect(url_for("assets.list_assets"))

    return render_template("assets/import.html", headers=EXPORT_HEADERS)
