(function () {
    const storedTheme = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", storedTheme);
})();

document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("theme-toggle-btn");
    const label = document.getElementById("theme-label");

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
        if (label) label.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
    }

    const currentTheme = document.documentElement.getAttribute("data-theme");
    if (label) label.textContent = currentTheme.charAt(0).toUpperCase() + currentTheme.slice(1);

    btn?.addEventListener("click", () => {
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        applyTheme(nextTheme);
        location.reload(); // ensures Bootstrap recalculates colors cleanly
    });
});
