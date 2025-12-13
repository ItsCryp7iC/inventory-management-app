from flask import render_template, redirect, url_for, flash
from flask_login import login_required
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional
from flask_wtf import FlaskForm

from . import bp
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import Setting


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
    )


@bp.route("/import-export")
@login_required
@admin_required
def import_export():
    from app.assets.routes import EXPORT_HEADERS  # reuse headers
    return render_template("settings/import_export.html", headers=EXPORT_HEADERS)
