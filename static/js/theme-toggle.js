(function () {
    const htmlEl = document.documentElement;
    const toggleBtn = document.getElementById("theme-toggle-btn");
    const themeLabel = document.getElementById("theme-label");

    const THEME_KEY = "inventory_theme";

    function applyTheme(theme) {
        if (theme !== "light" && theme !== "dark") {
            theme = "dark";
        }
        htmlEl.setAttribute("data-theme", theme);
        if (themeLabel) {
            themeLabel.textContent = theme === "dark" ? "Dark" : "Light";
        }
        localStorage.setItem(THEME_KEY, theme);
    }

    function toggleTheme() {
        const current = htmlEl.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        applyTheme(next);
    }

    // Initialize
    document.addEventListener("DOMContentLoaded", function () {
        const stored = localStorage.getItem(THEME_KEY);
        applyTheme(stored || "dark");

        if (toggleBtn) {
            toggleBtn.addEventListener("click", toggleTheme);
        }
    });
})();
