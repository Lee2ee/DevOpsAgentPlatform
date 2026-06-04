import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderSearch,
  Rocket,
  FileText,
  Settings,
  ClipboardList,
} from "lucide-react";

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/project", icon: FolderSearch, label: "Project" },
  { to: "/deploy", icon: Rocket, label: "Deploy" },
  { to: "/logs", icon: FileText, label: "Logs" },
  { to: "/activity", icon: ClipboardList, label: "Activity" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  return (
    <aside className="w-16 flex flex-col items-center bg-gray-900 py-4 gap-2">
      <div className="mb-4 text-brand-500 font-bold text-xs text-center leading-tight px-1">
        AI<br />Dev<br />Ops
      </div>
      {NAV.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          title={label}
          className={({ isActive }) =>
            `flex flex-col items-center gap-1 p-2 rounded-lg w-12 text-xs transition-colors ${
              isActive
                ? "bg-brand-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`
          }
        >
          <Icon size={18} />
          <span className="hidden">{label}</span>
        </NavLink>
      ))}
    </aside>
  );
}
