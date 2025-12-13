from flask import render_template, redirect, url_for, flash, request
from . import bp
from app.extensions import db
from app.models import Category, SubCategory

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional
from flask_login import login_required
from app.auth.decorators import admin_required



# -----------------------------
# Category Form
# -----------------------------
class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save")


# -----------------------------
# Sub-Category Form
# -----------------------------
class SubCategoryForm(FlaskForm):
    name = StringField("Sub-Category Name", validators=[DataRequired(), Length(max=100)])
    category_id = SelectField("Parent Category", coerce=int, validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save")


def _category_choices():
    """Return a list of (id, name) tuples for use in SelectField choices."""
    categories = Category.query.order_by(Category.name.asc()).all()
    return [(c.id, c.name) for c in categories]


# -----------------------------
# Category List
# -----------------------------
@bp.route("/")
@admin_required
def list_categories():
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template("categories/list.html", categories=categories)


# -----------------------------
# Category Create
# -----------------------------
@bp.route("/new", methods=["GET", "POST"])
@admin_required
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
@admin_required
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


# -----------------------------
# Sub-Category List
# -----------------------------
@bp.route("/subcategories")
@admin_required
def list_subcategories():
    subcategories = (
        SubCategory.query
        .join(Category, SubCategory.category_id == Category.id)
        .order_by(Category.name.asc(), SubCategory.name.asc())
        .all()
    )
    return render_template("categories/subcategories_list.html", subcategories=subcategories)


# -----------------------------
# Sub-Category Create
# -----------------------------
@bp.route("/subcategories/new", methods=["GET", "POST"])
@admin_required
def create_subcategory():
    choices = _category_choices()
    if not choices:
        flash("You must create at least one Category before adding Sub-Categories.", "danger")
        return redirect(url_for("categories.list_categories"))

    form = SubCategoryForm()
    form.category_id.choices = choices

    if form.validate_on_submit():
        subcat = SubCategory(
            name=form.name.data,
            category_id=form.category_id.data,
            description=form.description.data or None,
        )
        db.session.add(subcat)
        db.session.commit()
        flash("Sub-Category created successfully.", "success")
        return redirect(url_for("categories.list_subcategories"))

    return render_template("categories/subcategories_form.html", form=form, is_edit=False)


# -----------------------------
# Sub-Category Edit
# -----------------------------
@bp.route("/subcategories/<int:subcat_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_subcategory(subcat_id):
    subcat = SubCategory.query.get_or_404(subcat_id)

    choices = _category_choices()
    if not choices:
        flash("You must have at least one Category to manage Sub-Categories.", "danger")
        return redirect(url_for("categories.list_categories"))

    form = SubCategoryForm(obj=subcat)
    form.category_id.choices = choices

    if request.method == "GET":
        # Ensure the current category is selected correctly
        form.category_id.data = subcat.category_id

    if form.validate_on_submit():
        subcat.name = form.name.data
        subcat.category_id = form.category_id.data
        subcat.description = form.description.data or None

        db.session.commit()
        flash("Sub-Category updated successfully.", "success")
        return redirect(url_for("categories.list_subcategories"))

    return render_template("categories/subcategories_form.html", form=form, is_edit=True, subcat=subcat)
