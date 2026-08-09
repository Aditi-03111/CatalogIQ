import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  UploadCloud,
  Activity,
  Search,
  CheckSquare,
  HeartPulse,
  Settings
} from 'lucide-react';

interface SidebarItemProps {
  to: string;
  label: string;
  icon: React.ComponentType<any>;
}

const SidebarItem: React.FC<SidebarItemProps> = ({ to, label, icon: Icon }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
          isActive
            ? 'bg-primary text-primary-foreground shadow-lg'
            : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
        }`
      }
    >
      <Icon className="w-5 h-5 shrink-0" />
      <span>{label}</span>
    </NavLink>
  );
};

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r bg-card flex flex-col h-screen select-none">
      <div className="p-6 border-b flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-lg shadow-md">
          C
        </div>
        <div>
          <h1 className="font-bold text-base tracking-tight leading-none">CatalogIQ</h1>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Product Intelligence
          </span>
        </div>
      </div>
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        <SidebarItem to="/" label="Overview" icon={LayoutDashboard} />
        <SidebarItem to="/catalog" label="Catalog" icon={Database} />
        <SidebarItem to="/upload" label="Upload" icon={UploadCloud} />
        <SidebarItem to="/jobs" label="Processing Jobs" icon={Activity} />
        <SidebarItem to="/search" label="Search" icon={Search} />
        <SidebarItem to="/reviews" label="Reviews" icon={CheckSquare} />
        <SidebarItem to="/health" label="Catalog Health" icon={HeartPulse} />
      </nav>
      <div className="p-4 border-t">
        <SidebarItem to="/settings" label="Settings" icon={Settings} />
      </div>
    </aside>
  );
};
