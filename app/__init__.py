from flask import Flask

from .extensions import db, migrate


def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object("config.Config")

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Flask-Migrate can see them
    from . import models  # noqa

    # Register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    return app
