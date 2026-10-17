import { useEffect, useState } from "react";
import { ThemeProviderContext, type Theme } from "./theme-context";

function initialTheme(): Theme {
  // Lazy initializer avoids a synchronous setState in an effect.
  const stored = (typeof localStorage !== "undefined"
    ? localStorage.getItem("theme")
    : null) as Theme | null;
  return stored ?? "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <ThemeProviderContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeProviderContext.Provider>
  );
}
