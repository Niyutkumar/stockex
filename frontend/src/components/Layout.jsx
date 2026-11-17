/* The shell every signed-in screen sits inside: rail on the left, page
   content on the right. */

import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { Wordmark } from "./Logo";

const LINKS = [
  { to: "/", label: "Dashboard", end: true, icon: "grid" },
  { to: "/trade", label: "Record a trade", icon: "plus" },
  { to: "/transactions", label: "Transactions", icon: "list" },
  { to: "/watchlist", label: "Watchlist", icon: "eye" },
];

function Icon({ name }) {
  const common = {
    width: 15, height: 15, viewBox: "0 0 16 16", fill: "none",
    stroke: "currentColor", strokeWidth: 1.5, "aria-hidden": true,
    style: { flex: "none" },
  };
  if (name === "grid")
    return (
      <svg {...common}>
        <rect x="1.5" y="1.5" width="5.5" height="6.5" rx="1.5" />
        <rect x="9" y="1.5" width="5.5" height="4" rx="1.5" />
        <rect x="9" y="7" width="5.5" height="7.5" rx="1.5" />
        <rect x="1.5" y="9.5" width="5.5" height="5" rx="1.5" />
      </svg>
    );
  if (name === "plus")
    return <svg {...common}><path d="M8 3v10M3 8h10" strokeLinecap="round" /></svg>;
  if (name === "list")
    return (
      <svg {...common}>
        <rect x="2.5" y="1.75" width="11" height="12.5" rx="1.5" />
        <path d="M5.25 5.5h5.5M5.25 8h5.5M5.25 10.5h3" strokeLinecap="round" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="M1.5 8s2.4-4.5 6.5-4.5S14.5 8 14.5 8s-2.4 4.5-6.5 4.5S1.5 8 1.5 8Z" />
      <circle cx="8" cy="8" r="1.9" />
    </svg>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { isDark, toggle } = useTheme();
  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@._-]+/).filter(Boolean).slice(0, 2)
    .map((part) => part[0].toUpperCase()).join("");

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail-mark"><Wordmark /></div>
        <nav className="rail-nav">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}
                     className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon name={link.icon} />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="rail-foot">
          <div className="whoami">
            <div className="avatar">{initials}</div>
            <div style={{ minWidth: 0 }}>
              <b>{user?.full_name || "Signed in"}</b>
              <span>{user?.email}</span>
            </div>
          </div>
          <button className="ghost" onClick={toggle}
                  aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}>
            {isDark ? (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                <circle cx="8" cy="8" r="3.25" />
                <path d="M8 1v1.5M8 13.5V15M15 8h-1.5M2.5 8H1M12.95 3.05l-1.06 1.06M4.11 11.89l-1.06 1.06M12.95 12.95l-1.06-1.06M4.11 4.11 3.05 3.05" strokeLinecap="round" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                <path d="M13.5 9.6A5.8 5.8 0 0 1 6.4 2.5a5.8 5.8 0 1 0 7.1 7.1Z" strokeLinejoin="round" />
              </svg>
            )}
            {isDark ? "Light mode" : "Dark mode"}
          </button>
          <button className="ghost" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="work"><Outlet /></main>
    </div>
  );
}
