from flask import render_template, redirect, url_for, flash
from . import bp
from app.extensions import db
from app.models import Vendor

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from flask_login import login_required

class VendorForm(FlaskForm):
    name = StringField("Vendor Name", validators=[DataRequired(), Length(max=150)])
    contact_email = StringField("Contact Email", validators=[Optional(), Length(max=150)])
    contact_phone = StringField("Contact Phone", validators=[Optional(), Length(max=50)])
    website = StringField("Website", validators=[Optional(), Length(max=200)])
    address = TextAreaField("Address", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Save")


@bp.route("/")
@login_required
def list_vendors():
    vendors = Vendor.query.order_by(Vendor.name.asc()).all()
    return render_template("vendors/list.html", vendors=vendors)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create_vendor():
    form = VendorForm()

    if form.validate_on_submit():
        vendor = Vendor(
            name=form.name.data,
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
@login_required
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    form = VendorForm(obj=vendor)

    if form.validate_on_submit():
        vendor.name = form.name.data
        vendor.contact_email = form.contact_email.data or None
        vendor.contact_phone = form.contact_phone.data or None
        vendor.website = form.website.data or None
        vendor.address = form.address.data or None

        db.session.commit()
        flash("Vendor updated successfully.", "success")
        return redirect(url_for("vendors.list_vendors"))

    return render_template("vendors/form.html", form=form, is_edit=True, vendor=vendor)
