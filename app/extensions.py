from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_wtf.csrf import generate_csrf


db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    app.jinja_env.globals["csrf_token"] = generate_csrf



    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(current_user=current_user)


from app.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
