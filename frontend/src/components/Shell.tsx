import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Pill } from "../lib/ui";

const NAV = [
  { to: "/", label: "Home", icon: "◈", group: "" },
  { to: "/orders", label: "Production Orders", icon: "▣", group: "Enterprise (L4)" },
  { to: "/inventory", label: "Inventory", icon: "▤", group: "Enterprise (L4)" },
  { to: "/maintenance", label: "Plant Maintenance", icon: "⚙", group: "Enterprise (L4)" },
  { to: "/users", label: "Users & Roles", icon: "◉", group: "Enterprise (L4)" },
  { to: "/files", label: "Document Share", icon: "▦", group: "Enterprise (L4)" },
  { to: "/scada", label: "SCADA / HMI", icon: "◧", group: "Operations" },
  { to: "/engineering", label: "Engineering Station", icon: "⌁", group: "Operations" },
];

export default function Shell() {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const groups = [...new Set(NAV.map((n) => n.group))];

  return (
    <div className="h-screen flex flex-col">
      {/* top bar */}
      <header className="h-12 bg-shell-header text-white flex items-center px-4 gap-3 shrink-0 shadow">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-brand-500 grid place-items-center font-bold text-sm">K</div>
          <div className="font-semibold tracking-tight">Kaveri Process Industries</div>
          <span className="text-brand-200 text-xs ml-1">· ArenaPlant S/4</span>
        </div>
        <div className="ml-auto flex items-center gap-3 text-sm">
          <span className="text-brand-100">Plant 1000 · Bengaluru · Line 2</span>
          <div className="flex items-center gap-2 pl-3 border-l border-white/20">
            <div className="w-7 h-7 rounded-full bg-brand-300 text-brand-900 grid place-items-center text-xs font-bold">
              {user?.full_name?.split(" ").map((s) => s[0]).slice(0, 2).join("")}
            </div>
            <div className="leading-tight">
              <div className="text-xs font-medium">{user?.full_name}</div>
              <div className="text-[10px] text-brand-200 uppercase">{user?.role}</div>
            </div>
            <button onClick={logout} className="ml-2 text-brand-200 hover:text-white text-xs">Sign out</button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* sidebar */}
        <aside className="w-60 bg-shell-sidebar text-slate-200 overflow-y-auto shrink-0">
          <nav className="py-3">
            {groups.map((g) => (
              <div key={g} className="mb-1">
                {g && <div className="px-4 pt-3 pb-1 text-[10px] uppercase tracking-wider text-slate-400">{g}</div>}
                {NAV.filter((n) => n.group === g).map((n) => (
                  <NavLink key={n.to} to={n.to} end={n.to === "/"}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-4 py-2 text-sm transition ${
                        isActive ? "bg-brand-600 text-white" : "hover:bg-white/5 text-slate-300"}`}>
                    <span className="text-base opacity-80">{n.icon}</span>{n.label}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
          <div className="px-4 py-3 mt-2 border-t border-white/10 text-[11px] text-slate-400">
            <div className="flex items-center gap-2"><Pill tone="warn">SANDBOX</Pill></div>
            <p className="mt-2 leading-snug">Deliberately vulnerable test range. Not a real plant.</p>
          </div>
        </aside>

        {/* content */}
        <main key={loc.pathname} className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto p-5">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
