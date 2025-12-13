from flask import render_template, redirect, url_for, flash, abort
from . import bp
from app.extensions import db
from app.models import Vendor

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from flask_login import login_required
from app.auth.decorators import admin_required


class VendorForm(FlaskForm):
    name = StringField("Vendor Name", validators=[DataRequired(), Length(max=150)])
    code = StringField(
        "Vendor Code",
        validators=[Optional(), Length(max=20)],
        filters=[lambda x: x.strip().upper() if x else x],
        description="If left blank, code will be auto-generated (e.g., V001)."
    )
    contact_email = StringField("Contact Email", validators=[Optional(), Length(max=150)])
    contact_phone = StringField("Contact Phone", validators=[Optional(), Length(max=50)])
    website = StringField("Website", validators=[Optional(), Length(max=200)])
    address = TextAreaField("Address", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Save")


@bp.route("/")
@admin_required
def list_vendors():
    _normalize_existing_vendors()
    _assign_missing_codes()
    vendors = Vendor.query.order_by(Vendor.code.asc()).all()
    return render_template("vendors/list.html", vendors=vendors)


def _current_max_code_number():
    """
    Get the largest numeric suffix among vendor codes that match V###.
    Ignores legacy / non-standard codes so they don't inflate the sequence.
    """
    max_num = 0
    existing_codes = (
        Vendor.query.with_entities(Vendor.code).filter(Vendor.code.isnot(None)).all()
    )
    for (code,) in existing_codes:
        if not code:
            continue
        code_upper = code.upper().strip()
        if code_upper.startswith("V") and code_upper[1:].isdigit():
            max_num = max(max_num, int(code_upper[1:]))
    return max_num


def _generate_vendor_code():
    """
    Generate next vendor code like V001, V002 based on existing codes.
    """
    next_num = _current_max_code_number() + 1
    return f"V{next_num:03d}"


def _assign_missing_codes():
    missing = Vendor.query.filter((Vendor.code == None) | (Vendor.code == "")).all()  # noqa: E711
    if not missing:
        return
    next_num = _current_max_code_number()
    for vendor in missing:
        next_num += 1
        vendor.code = f"V{next_num:03d}"
    db.session.commit()


def _normalize_existing_vendors():
    """
    Clean up legacy data where the vendor name was stored in the code field.
    - If name is missing but code has text, move that text into name.
    - If code is missing or does not follow our V### pattern, assign a fresh code.
    """
    updated = False
    next_num = _current_max_code_number()
    vendors = Vendor.query.all()
    for vendor in vendors:
        # Move old name from code into name when name is missing
        if (vendor.name is None or vendor.name.strip() == "") and vendor.code:
            vendor.name = vendor.code
            updated = True

        # Decide if code needs regeneration
        needs_new_code = (
            vendor.code is None
            or vendor.code.strip() == ""
            or not vendor.code.upper().startswith("V")
            or not vendor.code.upper()[1:].isdigit()
        )
        if needs_new_code:
            next_num += 1
            vendor.code = f"V{next_num:03d}"
            updated = True

    if updated:
        db.session.commit()


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create_vendor():
    form = VendorForm()

    if form.validate_on_submit():
        code = form.code.data or _generate_vendor_code()
        if Vendor.query.filter_by(code=code).first():
            flash("Vendor code already exists. Please use a unique code.", "danger")
            return render_template("vendors/form.html", form=form, is_edit=False)

        vendor = Vendor(
            name=form.name.data,
            code=code,
            contact_email=form.contact_email.data or None,
            contact_phone=form.contact_phone.data or None,
            website=form.website.data or None,
            address=form.address.data or None,
        )
        db.session.add(vendor)
        db.session.commit()
        flash("Vendor created successfully.", "success")
        return redirect(url_for("vendors.list_vendors"))

    return render_template("vendors/form.html", form=form, is_edit=False)


@bp.route("/<int:vendor_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    form = VendorForm(obj=vendor)

    if form.validate_on_submit():
        if form.code.data:
            if form.code.data != vendor.code and Vendor.query.filter_by(code=form.code.data).first():
                flash("Vendor code already exists. Please use a unique code.", "danger")
                return render_template("vendors/form.html", form=form, is_edit=True, vendor=vendor)
            vendor.code = form.code.data
        vendor.name = form.name.data
        vendor.contact_email = form.contact_email.data or None
        vendor.contact_phone = form.contact_phone.data or None
        vendor.website = form.website.data or None
        vendor.address = form.address.data or None

        db.session.commit()
        flash("Vendor updated successfully.", "success")
        return redirect(url_for("vendors.list_vendors"))

    return render_template("vendors/form.html", form=form, is_edit=True, vendor=vendor)


@bp.route("/<int:vendor_id>/delete", methods=["POST"])
@admin_required
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    db.session.delete(vendor)
    db.session.commit()
    flash("Vendor deleted.", "success")
    return redirect(url_for("vendors.list_vendors"))
