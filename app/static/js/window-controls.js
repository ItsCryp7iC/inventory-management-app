// Provides Python bridge handlers for pywebview custom frame

class WindowAPI {
    minimize() {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.minimize) {
            window.pywebview.api.minimize();
        }
    }
    maximize() {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.maximize) {
            window.pywebview.api.maximize();
        }
    }
    close() {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.close) {
            window.pywebview.api.close();
        }
    }
}

window.windowControlsAPI = new WindowAPI();
