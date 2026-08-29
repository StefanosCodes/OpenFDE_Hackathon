import { MoreHorizontal, Plus } from "lucide-react";
import * as React from "react";
import { useNavigate } from "react-router-dom";

import { useAgents } from "@/app/providers/agent-provider";
import {
  getAgentDestination,
  getAgentStage,
} from "@/entities/agent/model/agent-state";
import type { Agent, AgentStage } from "@/entities/agent/model/types";
import { ConfirmDialog } from "@/shared/ui/confirm-dialog";
import { AgentsIcon } from "@/widgets/app-sidebar/ui/nav-icons";

function formatDate(timestamp: number) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(timestamp);
}

export function AgentsPage() {
  const navigate = useNavigate();
  const { agents, deleteAgent } = useAgents();
  const [menuOpenId, setMenuOpenId] = React.useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = React.useState<Agent | null>(null);

  return (
    <section className="page agents-page">
      <div className="page-inner">
        <header className="page-header page-header--split">
          <div>
            <h1>Agents</h1>
            <p>Design an agent through conversation, then bring it to life visually.</p>
          </div>
          <button
            type="button"
            className="button button--primary"
            onClick={() => navigate("/agents/new")}
          >
            <Plus size={16} />
            New agent
          </button>
        </header>

        <table className="data-table">
          <thead>
            <tr>
              <th className="th-name">Name</th>
              <th className="th-status">Status</th>
              <th className="th-created">Created</th>
              <th className="th-updated">Updated</th>
              <th className="th-actions">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {agents.length === 0 ? (
              <tr className="data-table__empty">
                <td colSpan={5}>No agents yet</td>
              </tr>
            ) : (
              agents.map((agent) => (
                <AgentRow
                  key={agent.id}
                  agent={agent}
                  menuOpen={menuOpenId === agent.id}
                  onOpen={() => navigate(getAgentDestination(agent))}
                  onToggleMenu={() =>
                    setMenuOpenId((current) =>
                      current === agent.id ? null : agent.id,
                    )
                  }
                  onCloseMenu={() => setMenuOpenId(null)}
                  onDelete={() => {
                    setMenuOpenId(null);
                    setPendingDelete(agent);
                  }}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete agent"
        description={
          pendingDelete
            ? `Delete “${pendingDelete.name}”? This cannot be undone.`
            : ""
        }
        confirmLabel="Delete"
        onClose={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) {
            deleteAgent(pendingDelete.id);
          }
        }}
      />
    </section>
  );
}

function AgentRow({
  agent,
  menuOpen,
  onOpen,
  onToggleMenu,
  onCloseMenu,
  onDelete,
}: {
  agent: Agent;
  menuOpen: boolean;
  onOpen: () => void;
  onToggleMenu: () => void;
  onCloseMenu: () => void;
  onDelete: () => void;
}) {
  const stage = getAgentStage(agent);
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!menuOpen) return;

    const onPointerDown = (event: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onCloseMenu();
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCloseMenu();
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen, onCloseMenu]);

  return (
    <tr
      className="data-table__row"
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
      role="link"
      tabIndex={0}
    >
      <td className="td-name">
        <div className="agent-cell">
          <span className="agent-mark" aria-hidden="true">
            <AgentsIcon size={16} />
          </span>
          <span className="agent-cell__title">{agent.name}</span>
        </div>
      </td>
      <td className="td-status">
        <StatusPill stage={stage} />
      </td>
      <td className="td-created">{formatDate(agent.createdAt)}</td>
      <td className="td-updated">{formatDate(agent.updatedAt)}</td>
      <td className="td-actions">
        <div
          className="row-menu"
          ref={menuRef}
          onClick={(event) => event.stopPropagation()}
          onKeyDown={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            className="row-menu__trigger"
            aria-label={`${agent.name} actions`}
            aria-expanded={menuOpen}
            onClick={onToggleMenu}
          >
            <MoreHorizontal size={16} />
          </button>
          {menuOpen ? (
            <div className="row-menu__panel" role="menu" aria-label={`${agent.name} actions`}>
              <button
                type="button"
                role="menuitem"
                className="row-menu__item"
                onClick={onDelete}
              >
                Delete
              </button>
            </div>
          ) : null}
        </div>
      </td>
    </tr>
  );
}

function StatusPill({ stage }: { stage: AgentStage }) {
  const className = `status-pill status-pill--${stage
    .toLowerCase()
    .replace(" ", "-")}`;
  return <span className={className}>{stage}</span>;
}
