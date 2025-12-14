import os
import sys
import webbrowser
from threading import Timer

from app import create_app

APP_NAME = "ITInventory"

# Precompute data dir so Config picks it up before app is created
data_root = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~"),
    APP_NAME,
    "data",
)
os.makedirs(data_root, exist_ok=True)
# Ensure Config sees this path on import
os.environ.setdefault("INVENTORY_DATA_DIR", data_root)

def app_data_dir(app_name=APP_NAME):
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, app_name)
    os.makedirs(path, exist_ok=True)
    return path

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

def create_config_overrides():
    """
    Force SQLite DB into a writable AppData folder.
    """
    data_root = os.path.join(app_data_dir(), "data")
    os.makedirs(data_root, exist_ok=True)

    db_path = os.path.join(data_root, "inventory.db")
    os.environ.setdefault("INVENTORY_DATA_DIR", data_root)
    return {
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # Optional: if you use Flask sessions / CSRF, keep secret stable
        # Put a real secret in production; for demo you can hardcode or load from file
    }

if __name__ == "__main__":
    # In frozen mode, ensure CWD points to the unpacked bundle for relative assets
    if hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)

    # Create app after env is set so Config picks up INVENTORY_DATA_DIR
    app = create_app()
    app.config.update(create_config_overrides())

    Timer(1, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
