from flask import render_template, redirect, url_for, flash, request
from . import bp
from app.extensions import db
from app.models import Asset, Location, Category, SubCategory, Vendor
from .forms import AssetForm


@bp.route("/")
def list_assets():
    assets = Asset.query.order_by(Asset.id.desc()).all()
    return render_template("assets/list.html", assets=assets)


@bp.route("/new", methods=["GET", "POST"])
def create_asset():
    form = AssetForm()

    # Populate dropdown choices
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

    # Default status
    if request.method == "GET" and not form.status.data:
        form.status.data = "in_use"

    # Default location = Mirpur DOHS Office
    if request.method == "GET":
        mirpur = Location.query.filter_by(name="Mirpur DOHS Office").first()
        if mirpur:
            form.location_id.data = mirpur.id

    if form.validate_on_submit():
        # Convert "0" (--- Select ---) to None
        def normalize_id(value):
            return value if value and value != 0 else None

        asset = Asset(
            asset_tag=form.asset_tag.data or None,
            name=form.name.data,
            description=form.description.data or None,
            serial_number=form.serial_number.data or None,
            status=form.status.data,
            purchase_date=form.purchase_date.data,
            warranty_expiry_date=form.warranty_expiry_date.data,
            cost=form.cost.data,
            category_id=normalize_id(form.category_id.data),
            subcategory_id=normalize_id(form.subcategory_id.data),
            location_id=normalize_id(form.location_id.data),
            vendor_id=normalize_id(form.vendor_id.data),
            notes=form.notes.data or None,
        )

        db.session.add(asset)
        db.session.commit()
        flash("Asset created successfully.", "success")
        return redirect(url_for("assets.list_assets"))

    if form.errors:
        flash("Please correct the errors in the form.", "danger")

    return render_template("assets/create.html", form=form)
