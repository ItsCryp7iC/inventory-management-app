import os
import sys
from flask import Flask
from .extensions import init_extensions
from datetime import date, timedelta, datetime
from app.extensions import db
import sqlalchemy
from app.models import User


def _base_path():
    """
    Resolve base path for templates/static for both source and PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def create_app():
    base_path = _base_path()
    template_folder = os.path.join(base_path, "app", "templates")
    static_folder = os.path.join(base_path, "app", "static")

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

    # Load config
    app.config.from_object("config.Config")

    # Init ALL extensions in ONE place
    init_extensions(app)

    # Import models so Flask-Migrate can detect them
    from . import models  # noqa

    # Register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .assets import bp as assets_bp
    app.register_blueprint(assets_bp)

    from .locations import bp as locations_bp
    app.register_blueprint(locations_bp)

    from .categories import bp as categories_bp
    app.register_blueprint(categories_bp)

    from .vendors import bp as vendors_bp
    app.register_blueprint(vendors_bp)

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    from .settings import bp as settings_bp
    app.register_blueprint(settings_bp)

    # Ensure database/tables exist (especially on first run in packaged mode)
    with app.app_context():
        try:
            db.create_all()
        except sqlalchemy.exc.SQLAlchemyError:
            # If the DB file is missing or path invalid, surface error during startup
            app.logger.exception("Database initialization failed.")
            raise

        # Seed a default admin for fresh DBs
        if User.query.count() == 0:
            admin = User(username="admin", is_admin=True)
            admin.set_password("123456")
            db.session.add(admin)
            db.session.commit()

    # Global Jinja helpers
    app.jinja_env.globals["date"] = date
    app.jinja_env.globals["timedelta"] = timedelta

    # Date/time formatting filters
    def fmt_date(value):
        if not value:
            return "-"
        if isinstance(value, datetime):
            value = value.date()
        try:
            return value.strftime("%d-%m-%Y")
        except Exception:
            return str(value)

    def fmt_datetime(value):
        if not value:
            return "-"
        if isinstance(value, datetime):
            return value.strftime("%d-%m-%Y - %H:%M:%S")
        try:
            # Try to coerce date objects
            return fmt_date(value)
        except Exception:
            return str(value)

    app.jinja_env.filters["fmt_date"] = fmt_date
    app.jinja_env.filters["fmt_datetime"] = fmt_datetime

    # Settings helper for templates
    from app.settings.routes import get_setting_value  # lightweight helper
    app.jinja_env.globals["get_setting"] = get_setting_value

    from flask import render_template

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    return app
