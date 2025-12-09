from flask import render_template, redirect, url_for, flash, request
from . import bp
from app.extensions import db
from app.models import Category, SubCategory

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


# -----------------------------
# Category Form
# -----------------------------
class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save")


# -----------------------------
# Category List
# -----------------------------
@bp.route("/")
def list_categories():
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template("categories/list.html", categories=categories)


# -----------------------------
# Category Create
# -----------------------------
@bp.route("/new", methods=["GET", "POST"])
def create_category():
    form = CategoryForm()

    if form.validate_on_submit():
        cat = Category(
            name=form.name.data,
            description=form.description.data or None,
        )
        db.session.add(cat)
        db.session.commit()
        flash("Category created successfully.", "success")
        return redirect(url_for("categories.list_categories"))

    return render_template("categories/form.html", form=form, is_edit=False)


# -----------------------------
# Category Edit
# -----------------------------
@bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
def edit_category(category_id):
    cat = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=cat)

    if form.validate_on_submit():
        cat.name = form.name.data
        cat.description = form.description.data or None
        db.session.commit()
        flash("Category updated successfully.", "success")
        return redirect(url_for("categories.list_categories"))

    return render_template("categories/form.html", form=form, is_edit=True, cat=cat)
