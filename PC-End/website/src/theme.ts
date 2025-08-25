import { useEffect, useState } from "react";

export type Theme = "default" | "blue" | "gruvbox-dark" | "gruvbox-light";

const THEME_KEY = "telemetry.theme";

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = (localStorage.getItem(THEME_KEY) || "default") as Theme;
    if (saved === "blue" || saved === "gruvbox-dark" || saved === "gruvbox-light") return saved;
    return "default";
  });

  useEffect(() => {
    const root = document.documentElement;
    const classes = Array.from(root.classList);
    for (const c of classes) {
      if (c.startsWith("theme-")) root.classList.remove(c);
    }
    root.classList.add(`theme-${theme}`);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  return [theme, setTheme];
}

