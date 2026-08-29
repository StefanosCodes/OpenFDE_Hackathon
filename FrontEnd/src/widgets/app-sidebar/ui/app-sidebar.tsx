import { PanelLeft, Search, Settings } from "lucide-react";
import * as React from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

import { AgentSearchDialog } from "@/widgets/app-sidebar/ui/agent-search-dialog";
import { AgentsIcon, ConnectorsIcon } from "@/widgets/app-sidebar/ui/nav-icons";
import { OpenFDEMark } from "@/widgets/app-sidebar/ui/openfde-mark";

const SIDEBAR_KEY = "openfde-sidebar-collapsed";

export function AppSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [collapsed, setCollapsed] = React.useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) === "true";
    } catch {
      return false;
    }
  });

  const persistCollapsed = (next: boolean) => {
    setCollapsed(next);
    try {
      localStorage.setItem(SIDEBAR_KEY, String(next));
    } catch {
      // Keep the UI working without browser persistence.
    }
  };

  React.useEffect(() => {
    const path = location.pathname;
    const isWorkspace =
      path === "/agents/new" ||
      /^\/agents\/[^/]+\/(design|canvas)$/.test(path);
    persistCollapsed(isWorkspace);
  }, [location.pathname]);

  const toggle = () => {
    persistCollapsed(!collapsed);
  };

  return (
    <aside className={collapsed ? "sidebar sidebar--collapsed" : "sidebar"}>
      <div className="sidebar__header">
        <button
          type="button"
          className="brand"
          aria-label={collapsed ? "Open sidebar" : "Go to agents"}
          onClick={() => {
            if (collapsed) {
              toggle();
              return;
            }
            navigate("/agents");
          }}
        >
          <OpenFDEMark className="brand__mark" />
          <span className="brand__name">OpenFDE</span>
        </button>
        {collapsed ? null : (
          <div className="sidebar__header-actions">
            <button
              type="button"
              className="icon-button"
              aria-label="Search agents"
              onClick={() => setSearchOpen(true)}
            >
              <Search size={16} />
            </button>
            <button
              type="button"
              className="icon-button"
              aria-label="Close sidebar"
              onClick={toggle}
            >
              <PanelLeft size={16} />
            </button>
          </div>
        )}
      </div>

      <nav className="sidebar__nav" aria-label="Main navigation">
        <SidebarLink to="/agents" label="Agents" collapsed={collapsed}>
          <AgentsIcon />
        </SidebarLink>
        <SidebarLink to="/connectors" label="Connectors" collapsed={collapsed}>
          <ConnectorsIcon />
        </SidebarLink>
      </nav>

      <div className="sidebar__footer">
        <div className="account-row" title={collapsed ? "Demo account" : undefined}>
          <Settings size={16} />
          {!collapsed ? <span>Account</span> : null}
        </div>
      </div>

      <AgentSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
      />
    </aside>
  );
}

function SidebarLink({
  to,
  label,
  collapsed,
  children,
}: {
  to: string;
  label: string;
  collapsed: boolean;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        isActive ? "sidebar-link sidebar-link--active" : "sidebar-link"
      }
    >
      {children}
      {!collapsed ? <span>{label}</span> : null}
    </NavLink>
  );
}
