from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional
from flask_wtf import FlaskForm
from datetime import datetime
from pathlib import Path
import shutil
import os

from . import bp
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import Setting, Asset, AssetEvent, AssetTagSequence, Location, Category, SubCategory, Vendor, User
from app.assets.routes import EXPORT_HEADERS


def get_setting_value(key: str, default=None):
    setting = Setting.query.filter_by(key=key).first()
    if setting and setting.value is not None:
        return setting.value
    return default


def set_setting_value(key: str, value):
    setting = Setting.query.filter_by(key=key).first()
    if not setting:
        setting = Setting(key=key, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    return setting


class GeneralSettingsForm(FlaskForm):
    app_name = StringField("Application Name", validators=[DataRequired(), Length(max=150)])
    support_email = StringField("Support Email", validators=[Optional(), Email(), Length(max=150)])
    asset_tag_prefix = StringField(
        "Asset Tag Prefix",
        validators=[DataRequired(), Length(max=20)],
        description="Prefix used when auto-generating asset tags (e.g., ESS-)."
    )
    submit = SubmitField("Save Settings")


@bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def general_settings():
    form = GeneralSettingsForm()

    # Paths for backup/restore
    data_dir = Path(os.environ.get("INVENTORY_DATA_DIR", Path.cwd() / "data"))
    db_file = data_dir / "inventory.db"
    backup_dir = data_dir.parent / "Data Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    def list_backups():
        if not backup_dir.exists():
            return []
        files = sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [
            {
                "name": f.name,
                "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for f in files
        ]

    if form.validate_on_submit():
        set_setting_value("app_name", form.app_name.data.strip())
        set_setting_value("support_email", form.support_email.data.strip() or None)
        prefix_val = form.asset_tag_prefix.data.strip()
        if not prefix_val.endswith("-"):
            prefix_val = f"{prefix_val}-"
        set_setting_value("asset_tag_prefix", prefix_val)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("settings.general_settings"))

    if not form.is_submitted():
        form.app_name.data = get_setting_value("app_name", "IT Inventory")
        form.support_email.data = get_setting_value("support_email", "")
        form.asset_tag_prefix.data = get_setting_value("asset_tag_prefix", "ESS-")

    from app.assets.routes import EXPORT_HEADERS

    return render_template(
        "settings/index.html",
        form=form,
        export_headers=EXPORT_HEADERS,
        backups=list_backups(),
    )


@bp.route("/import-export")
@login_required
@admin_required
def import_export():
    from app.assets.routes import EXPORT_HEADERS  # reuse headers
    return render_template("settings/import_export.html", headers=EXPORT_HEADERS)


@bp.route("/reset-app", methods=["POST"])
@login_required
@admin_required
def reset_app_data():
    """
    Danger zone: wipe all domain data except admin users.
    """
    confirm = request.form.get("confirm_text", "").strip()
    if confirm != "DELETE":
        flash('Type "DELETE" exactly to confirm.', "danger")
        return redirect(url_for("settings.general_settings"))

    # Delete in dependency-safe order
    db.session.query(AssetEvent).delete()
    db.session.query(AssetTagSequence).delete()
    db.session.query(Asset).delete()
    db.session.query(SubCategory).delete()
    db.session.query(Category).delete()
    db.session.query(Location).delete()
    db.session.query(Vendor).delete()
    # Remove non-admin users
    db.session.query(User).filter(User.is_admin == False).delete()  # noqa: E712

    db.session.commit()
    flash("All data wiped. Admin users remain.", "success")
    return redirect(url_for("settings.general_settings"))


@bp.route("/asset-labels")
@login_required
@admin_required
def asset_labels_sheet():
    assets = Asset.query.order_by(Asset.asset_tag.asc()).all()
    return render_template("assets/labels_sheet.html", assets=assets)


@bp.route("/backup", methods=["POST"])
@login_required
@admin_required
def create_backup():
    data_dir = Path(os.environ.get("INVENTORY_DATA_DIR", Path.cwd() / "data"))
    db_file = data_dir / "inventory.db"
    backup_dir = data_dir.parent / "Data Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not db_file.exists():
        flash("No database file found to back up.", "danger")
        return redirect(url_for("settings.general_settings"))

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"inventory-backup-{timestamp}.db"
    try:
        shutil.copy2(db_file, backup_path)
        flash(f"Backup created: {backup_path.name}", "success")
    except Exception as exc:
        flash(f"Backup failed: {exc}", "danger")

    return redirect(url_for("settings.general_settings"))


@bp.route("/restore", methods=["POST"])
@login_required
@admin_required
def restore_backup():
    filename = request.form.get("backup_file", "")
    data_dir = Path(os.environ.get("INVENTORY_DATA_DIR", Path.cwd() / "data"))
    db_file = data_dir / "inventory.db"
    backup_dir = data_dir.parent / "Data Backups"
    src = backup_dir / filename

    if not filename or not src.exists():
        flash("Selected backup not found.", "danger")
        return redirect(url_for("settings.general_settings"))

    try:
        if db_file.exists():
            safety = db_file.with_suffix(".pre-restore.db")
            shutil.copy2(db_file, safety)
        shutil.copy2(src, db_file)
        flash(f"Restored backup: {filename}. Recent changes may be lost.", "warning")
    except Exception as exc:
        flash(f"Restore failed: {exc}", "danger")

    return redirect(url_for("settings.general_settings"))


@bp.route("/backup/assets-csv", methods=["POST"])
@login_required
@admin_required
def backup_assets_csv_to_file():
    data_dir = Path(os.environ.get("INVENTORY_DATA_DIR", Path.cwd() / "data"))
    backup_dir = data_dir.parent / "Data Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Get all assets
    assets = Asset.query.all()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"assets-export-{timestamp}.csv"

    try:
        import io, csv
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
        with open(dest, "w", encoding="utf-8", newline="") as f:
            f.write(output.getvalue())
        flash(f"Assets CSV saved to backups: {dest.name}", "success")
    except Exception as exc:
        flash(f"Assets CSV backup failed: {exc}", "danger")

    return redirect(url_for("settings.general_settings"))


@bp.route("/backup/categories-csv", methods=["POST"])
@login_required
@admin_required
def backup_categories_csv_to_file():
    data_dir = Path(os.environ.get("INVENTORY_DATA_DIR", Path.cwd() / "data"))
    backup_dir = data_dir.parent / "Data Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"categories-export-{timestamp}.csv"

    try:
        import io, csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["category_code", "category_name", "category_description", "subcategory_name", "subcategory_description"])

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

        with open(dest, "w", encoding="utf-8", newline="") as f:
            f.write(output.getvalue())
        flash(f"Categories CSV saved to backups: {dest.name}", "success")
    except Exception as exc:
        flash(f"Categories CSV backup failed: {exc}", "danger")

    return redirect(url_for("settings.general_settings"))
