from flask import render_template, redirect, url_for, flash, request, make_response
import io
import csv
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
    code = StringField(
        "Code",
        validators=[DataRequired(), Length(max=20)],
        filters=[lambda x: x.strip().upper() if x else x],
    )
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
            code=form.code.data,
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
        cat.code = form.code.data
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


@bp.route("/<int:category_id>/delete", methods=["POST"])
@admin_required
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted.", "success")
    return redirect(url_for("categories.list_categories"))


@bp.route("/subcategories/<int:subcat_id>/delete", methods=["POST"])
@admin_required
def delete_subcategory(subcat_id):
    subcat = SubCategory.query.get_or_404(subcat_id)
    db.session.delete(subcat)
    db.session.commit()
    flash("Sub-Category deleted.", "success")
    return redirect(url_for("categories.list_subcategories"))


# -----------------------------
# Import / Export (Backup)
# -----------------------------

@bp.route("/export")
@admin_required
def export_categories():
    """Export categories and sub-categories as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "category_code",
        "category_name",
        "category_description",
        "subcategory_name",
        "subcategory_description",
    ])

    categories = Category.query.order_by(Category.code.asc()).all()
    for cat in categories:
        if cat.subcategories:
            for sc in cat.subcategories:
                writer.writerow([
                    cat.code or "",
                    cat.name or "",
                    cat.description or "",
                    sc.name or "",
                    sc.description or "",
                ])
        else:
            writer.writerow([
                cat.code or "",
                cat.name or "",
                cat.description or "",
                "",
                "",
            ])

    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=categories_backup.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp


@bp.route("/import", methods=["POST"])
@admin_required
def import_categories():
    """Import categories and sub-categories from CSV."""
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Please select a CSV file to import.", "danger")
        return redirect(request.referrer or url_for("settings.general_settings"))

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"))
    except UnicodeDecodeError:
        flash("Unable to read file. Ensure it is UTF-8 encoded CSV.", "danger")
        return redirect(request.referrer or url_for("settings.general_settings"))

    reader = csv.DictReader(stream)
    required_cols = {"category_code", "category_name"}
    if not required_cols.issubset(set(reader.fieldnames or [])):
        flash(f"CSV must include headers: {', '.join(required_cols)}", "danger")
        return redirect(request.referrer or url_for("settings.general_settings"))

    created_cats = updated_cats = created_subs = updated_subs = 0
    for row in reader:
        cat_code = (row.get("category_code") or "").strip().upper()
        cat_name = (row.get("category_name") or "").strip()
        cat_desc = (row.get("category_description") or "").strip()
        sub_name = (row.get("subcategory_name") or "").strip()
        sub_desc = (row.get("subcategory_description") or "").strip()

        if not cat_code or not cat_name:
            continue

        category = Category.query.filter_by(code=cat_code).first()
        if not category:
            category = Category(code=cat_code, name=cat_name, description=cat_desc or None)
            db.session.add(category)
            created_cats += 1
            db.session.flush()
        else:
            if category.name != cat_name or category.description != (cat_desc or None):
                category.name = cat_name
                category.description = cat_desc or None
                updated_cats += 1
                db.session.flush()

        if sub_name:
            sub = SubCategory.query.filter_by(name=sub_name, category_id=category.id).first()
            if not sub:
                sub = SubCategory(name=sub_name, category_id=category.id, description=sub_desc or None)
                db.session.add(sub)
                created_subs += 1
            else:
                if sub.description != (sub_desc or None):
                    sub.description = sub_desc or None
                    updated_subs += 1

    db.session.commit()
    flash(
        f"Import complete. Categories created/updated: {created_cats}/{updated_cats}. "
        f"Sub-Categories created/updated: {created_subs}/{updated_subs}.",
        "success",
    )
    return redirect(request.referrer or url_for("settings.general_settings"))
