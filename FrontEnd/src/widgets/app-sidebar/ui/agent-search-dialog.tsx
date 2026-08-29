import { Search, X } from "lucide-react";
import * as React from "react";
import { useNavigate } from "react-router-dom";

import { useAgents } from "@/app/providers/agent-provider";
import { getAgentDestination } from "@/entities/agent/model/agent-state";
import { AgentsIcon } from "@/widgets/app-sidebar/ui/nav-icons";

export function AgentSearchDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const { agents } = useAgents();
  const [query, setQuery] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const normalized = query.trim().toLowerCase();
  const visible = agents.filter((agent) =>
    agent.name.toLowerCase().includes(normalized),
  );

  return (
    <div className="confirm-overlay" onClick={onClose}>
      <div
        className="search-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="search-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="search-dialog-title" className="sr-only">
          Search agents
        </h2>
        <div className="search-dialog__header">
          <Search size={16} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search agents"
            aria-label="Search agents"
          />
          <button
            type="button"
            className="icon-button"
            aria-label="Close search"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>
        <div className="search-dialog__list">
          <p className="search-dialog__label">Agents</p>
          {visible.length === 0 ? (
            <p className="search-dialog__empty">
              {agents.length === 0
                ? "No agents yet."
                : "No agents match your search."}
            </p>
          ) : (
            <ul>
              {visible.map((agent) => (
                <li key={agent.id}>
                  <button
                    type="button"
                    className="search-dialog__item"
                    onClick={() => {
                      navigate(getAgentDestination(agent));
                      onClose();
                    }}
                  >
                    <span className="agent-mark" aria-hidden="true">
                      <AgentsIcon size={16} />
                    </span>
                    <span>{agent.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
