import { useState } from "react";
export function ThemeSelector() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem("semi-theme") || "light",
  );
  return (
    <label className="theme-selector">
      Apariencia
      <select
        aria-label="Apariencia"
        value={theme}
        onChange={(e) => {
          const value = e.target.value;
          localStorage.setItem("semi-theme", value);
          setTheme(value);
          window.dispatchEvent(new Event("semi-theme"));
        }}
      >
        <option value="light">Claro</option>
        <option value="dark">Oscuro</option>
        <option value="system">Según el sistema</option>
      </select>
    </label>
  );
}
