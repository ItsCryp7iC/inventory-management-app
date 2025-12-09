from flask import Flask

from .extensions import db, migrate, csrf


def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object("config.Config")

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Import models so Flask-Migrate can see them
    from . import models  # noqa

    # Register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .assets import bp as assets_bp
    app.register_blueprint(assets_bp)

    from .locations import bp as locations_bp
    app.register_blueprint(locations_bp)

    # Jinja globals (date/time helpers for dashboard)
    from datetime import date, timedelta
    app.jinja_env.globals["date"] = date
    app.jinja_env.globals["timedelta"] = timedelta

    return app
