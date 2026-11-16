// Runs before CSS and React to avoid flashing a light surface on dark startup.
(() => {
  const media = matchMedia("(prefers-color-scheme: dark)");
  function apply() {
    let value = "light";
    try {
      value = localStorage.getItem("semi-theme") || "light";
    } catch {}
    document.documentElement.dataset.theme =
      value === "system" ? (media.matches ? "dark" : "light") : value;
    document.documentElement.style.colorScheme =
      document.documentElement.dataset.theme;
  }
  apply();
  media.addEventListener("change", apply);
  window.addEventListener("semi-theme", apply);
})();
