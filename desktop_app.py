import os
import sys
import threading
import time
import webview

from app import create_app
from run_app import create_config_overrides, data_root


class AppAPI:
    def minimize(self):
        if webview.windows:
            webview.windows[0].minimize()

    def maximize(self):
        if webview.windows:
            win = webview.windows[0]
            try:
                win.toggle_fullscreen()  # fallback behavior
            except Exception:
                win.maximize()

    def close(self):
        if webview.windows:
            webview.windows[0].destroy()


def resource_path(relative_path: str) -> str:
    """
    Resolve paths for both source and PyInstaller (_MEIPASS).
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def start_flask(app):
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def main():
    # Ensure we run from bundle path when frozen
    if hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)

    # Re-apply data dir env (important when launched directly)
    os.environ.setdefault("INVENTORY_DATA_DIR", data_root)

    app = create_app()
    app.config.update(create_config_overrides())

    flask_thread = threading.Thread(target=start_flask, args=(app,), daemon=True)
    flask_thread.start()

    # Small delay to let Flask start
    time.sleep(1)

    window = webview.create_window(
        "IT Inventory",
        "http://127.0.0.1:5000",
        width=1200,
        height=800,
        resizable=True,
        confirm_close=True,
        background_color="#0b1020",
        frameless=False,  # use native frame for compatibility
    )
    webview.start(debug=False, http_server=True)


if __name__ == "__main__":
    main()
