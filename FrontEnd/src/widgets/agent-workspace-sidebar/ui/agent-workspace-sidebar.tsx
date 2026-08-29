import {
  BookOpen,
  Database,
  GitBranch,
  MessageSquare,
  PanelLeft,
  Settings,
} from "lucide-react";
import * as React from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { OpenFDEMark } from "@/widgets/app-sidebar/ui/openfde-mark";

const SIDEBAR_KEY = "openfde-agent-workspace-sidebar-collapsed";

export function AgentWorkspaceSidebar({ agentId }: { agentId: string }) {
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = React.useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) === "true";
    } catch {
      return false;
    }
  });

  const toggle = () => {
    setCollapsed((current) => {
      const next = !current;
      try {
        localStorage.setItem(SIDEBAR_KEY, String(next));
      } catch {
        // Keep the UI working without browser persistence.
      }
      return next;
    });
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
              aria-label="Close sidebar"
              onClick={toggle}
            >
              <PanelLeft size={16} />
            </button>
          </div>
        )}
      </div>

      <nav className="sidebar__nav" aria-label="Agent workspace">
        <SidebarLink
          to={`/agents/${agentId}/canvas`}
          label="Visual map"
          collapsed={collapsed}
        >
          <GitBranch size={16} />
        </SidebarLink>
        <SidebarLink
          to={`/agents/${agentId}/knowledge`}
          label="Knowledge"
          collapsed={collapsed}
        >
          <BookOpen size={16} />
        </SidebarLink>
        <SidebarLink
          to={`/agents/${agentId}/intents`}
          label="Intents"
          collapsed={collapsed}
        >
          <MessageSquare size={16} />
        </SidebarLink>
        <SidebarLink
          to={`/agents/${agentId}/datasets`}
          label="Data sets"
          collapsed={collapsed}
        >
          <Database size={16} />
        </SidebarLink>
      </nav>

      <div className="sidebar__footer">
        <div className="account-row" title={collapsed ? "Demo account" : undefined}>
          <Settings size={16} />
          {!collapsed ? <span>Account</span> : null}
        </div>
      </div>
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
