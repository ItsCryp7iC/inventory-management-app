(function () {
    const storedTheme = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", storedTheme);
})();

document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("theme-toggle-btn");
    const sidebarToggle = document.getElementById("sidebar-toggle");

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
        if (btn) btn.setAttribute("data-theme", theme);
    }

    const initialTheme = document.documentElement.getAttribute("data-theme") || "dark";
    applyTheme(initialTheme);

    btn?.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        applyTheme(next);
    });

    // Sidebar collapse toggle
    const sidebarStateKey = "sidebar-collapsed";
    const body = document.body;

    function applySidebar(collapsed) {
        if (collapsed) {
            body.classList.add("sidebar-collapsed");
            if (sidebarToggle) sidebarToggle.textContent = ">";
            localStorage.setItem(sidebarStateKey, "1");
        } else {
            body.classList.remove("sidebar-collapsed");
            if (sidebarToggle) sidebarToggle.textContent = "<";
            localStorage.removeItem(sidebarStateKey);
        }
    }

    const storedSidebar = localStorage.getItem(sidebarStateKey) === "1";
    applySidebar(storedSidebar);

    sidebarToggle?.addEventListener("click", () => {
        const collapsed = body.classList.contains("sidebar-collapsed");
        applySidebar(!collapsed);
    });
});
