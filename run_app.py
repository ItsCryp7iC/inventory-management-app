import os
import sys
from app import create_app

APP_NAME = "ITInventory"

# Precompute data dir next to the executable/script so data travels with the app
base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.abspath(os.path.dirname(__file__))
data_root = os.path.join(base_dir, "data")
os.makedirs(data_root, exist_ok=True)
# Ensure Config sees this path on import
os.environ.setdefault("INVENTORY_DATA_DIR", data_root)

def create_config_overrides():
    """
    Force SQLite DB into a writable folder beside the app.
    """
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

    app.run(host="127.0.0.1", port=5000, debug=False)
