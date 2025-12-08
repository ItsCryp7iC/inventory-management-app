from flask import Flask
from .extensions import db, migrate, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Init extensions ONCE
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Import models
    from . import models  # noqa

    # Register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .assets import bp as assets_bp
    app.register_blueprint(assets_bp)

    return app
