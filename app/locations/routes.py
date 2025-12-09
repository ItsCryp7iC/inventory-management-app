from flask import render_template, redirect, url_for, flash, request
from . import bp
from app.extensions import db
from app.models import Location

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class LocationForm(FlaskForm):
    name = StringField("Location Name", validators=[DataRequired(), Length(max=100)])
    code = StringField("Code", validators=[Optional(), Length(max=50)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    is_active = BooleanField("Active")
    submit = SubmitField("Save")


@bp.route("/")
def list_locations():
    locations = Location.query.order_by(Location.name.asc()).all()
    return render_template("locations/list.html", locations=locations)


@bp.route("/new", methods=["GET", "POST"])
def create_location():
    form = LocationForm()

    if form.validate_on_submit():
        loc = Location(
            name=form.name.data,
            code=form.code.data or None,
            description=form.description.data or None,
            is_active=form.is_active.data,
        )
        db.session.add(loc)
        db.session.commit()
        flash("Location created successfully.", "success")
        return redirect(url_for("locations.list_locations"))

    return render_template("locations/form.html", form=form, is_edit=False)


@bp.route("/<int:location_id>/edit", methods=["GET", "POST"])
def edit_location(location_id):
    loc = Location.query.get_or_404(location_id)
    form = LocationForm(obj=loc)

    if form.validate_on_submit():
        loc.name = form.name.data
        loc.code = form.code.data or None
        loc.description = form.description.data or None
        loc.is_active = form.is_active.data

        db.session.commit()
        flash("Location updated successfully.", "success")
        return redirect(url_for("locations.list_locations"))

    return render_template("locations/form.html", form=form, is_edit=True, loc=loc)
