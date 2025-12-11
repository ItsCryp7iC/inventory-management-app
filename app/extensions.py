from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def init_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(current_user=current_user)


# Required by Flask-Login to load users from DB
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
