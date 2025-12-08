import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")  # change in production

    # SQLite DB file in project directory by default
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "inventory.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
