import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _db_uri():
    # Prefer external data dir for packaged app
    data_dir = os.environ.get("INVENTORY_DATA_DIR")
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        return "sqlite:///" + os.path.join(data_dir, "inventory.db")

    # Fallback to DATABASE_URL or local sqlite
    return os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "inventory.db"),
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")  # change in production
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
