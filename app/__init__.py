from flask import Flask

from .extensions import init_extensions   # IMPORTANT: import the initializer


def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object("config.Config")

    # Init ALL extensions (db, migrate, csrf, login_manager, context_processor)
    init_extensions(app)

    # Import models so Flask-Migrate can detect them
    from . import models  # noqa

    # Register blueprints (AFTER extensions are initialized)
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

    # Global Jinja helpers
    from datetime import date, timedelta
    app.jinja_env.globals["date"] = date
    app.jinja_env.globals["timedelta"] = timedelta

    return app
