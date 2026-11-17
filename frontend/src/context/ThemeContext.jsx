/* Light / dark, remembered per browser.
 *
 * Three states, not two: "light", "dark", and no stored choice at all —
 * in which case the CSS follows the operating system. The toggle writes
 * data-theme onto <html>, which is what the overriding token blocks in
 * theme.css key off.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";

const KEY = "stockex.theme";
const ThemeContext = createContext(null);

function stored() {
  try {
    const value = localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

function systemPrefersDark() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

export function ThemeProvider({ children }) {
  const [choice, setChoice] = useState(stored);

  useEffect(() => {
    const root = document.documentElement;
    if (choice) root.setAttribute("data-theme", choice);
    else root.removeAttribute("data-theme");

    try {
      if (choice) localStorage.setItem(KEY, choice);
      else localStorage.removeItem(KEY);
    } catch {
      /* storage unavailable; the choice still applies for this visit */
    }
  }, [choice]);

  const isDark = choice ? choice === "dark" : systemPrefersDark();
  const toggle = useCallback(() => {
    setChoice(isDark ? "light" : "dark");
  }, [isDark]);

  return (
    <ThemeContext.Provider value={{ choice, isDark, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme must be used inside <ThemeProvider>");
  return value;
}
