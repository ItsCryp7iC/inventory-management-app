from flask import Flask
from .extensions import init_extensions


def create_app():
    app = Flask(__name__)

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

    # Global Jinja helpers
    from datetime import date, timedelta
    app.jinja_env.globals["date"] = date
    app.jinja_env.globals["timedelta"] = timedelta

    from flask import render_template

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    return app
