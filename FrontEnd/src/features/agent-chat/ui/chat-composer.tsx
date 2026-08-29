import { ArrowUp } from "lucide-react";
import * as React from "react";

import { getConnector } from "@/entities/connector/model/connectors";
import { ConnectorIcon } from "@/entities/connector/ui/connector-icon";
import { InvokePalette } from "@/features/agent-chat/ui/invoke-palette";

function getSlashQuery(value: string): string | null {
  const match = value.match(/(?:^|\s)\/([^\s/]*)$/);
  return match ? match[1] : null;
}

function stripTrailingSlash(value: string) {
  return value.replace(/(^|\s)\/[^\s/]*$/, "$1").trimEnd();
}

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  placeholder = "Describe the agent you want to build",
  showConnectors = true,
  enabledConnectorIds,
  onToggleConnector,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  showConnectors?: boolean;
  enabledConnectorIds: string[];
  onToggleConnector: (id: string) => void;
}) {
  const rootRef = React.useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = React.useState(false);
  const slashQuery = getSlashQuery(value);
  const slashOpen = showConnectors && slashQuery !== null;
  const paletteOpen = showConnectors && (menuOpen || slashOpen);

  React.useEffect(() => {
    if (slashOpen) setMenuOpen(false);
  }, [slashOpen]);

  React.useEffect(() => {
    if (!paletteOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setMenuOpen(false);
      if (slashOpen) onChange(stripTrailingSlash(value));
    };
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current?.contains(event.target as Node)) return;
      setMenuOpen(false);
      if (slashOpen) onChange(stripTrailingSlash(value));
    };

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [paletteOpen, slashOpen, value, onChange]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (paletteOpen) return;
      if (value.trim()) onSubmit();
    }
  };

  return (
    <div className="composer-stack" ref={rootRef}>
      <div className="composer-shell">
        {paletteOpen ? (
          <InvokePalette
            query={slashQuery ?? ""}
            enabledIds={enabledConnectorIds}
            onToggle={onToggleConnector}
          />
        ) : null}

        <div className="chat-composer">
          <textarea
            aria-label="Message"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
          />
          <button
            type="button"
            className="composer-send"
            aria-label="Send message"
            disabled={!value.trim()}
            onClick={onSubmit}
          >
            <ArrowUp size={16} />
          </button>
        </div>
      </div>

      {showConnectors ? (
        <ConnectorWorkbar
          enabledIds={enabledConnectorIds}
          expanded={paletteOpen}
          onOpen={() => {
            if (slashOpen) {
              onChange(stripTrailingSlash(value));
            }
            setMenuOpen((current) => !current);
          }}
        />
      ) : null}
    </div>
  );
}

function ConnectorWorkbar({
  enabledIds,
  expanded,
  onOpen,
}: {
  enabledIds: string[];
  expanded: boolean;
  onOpen: () => void;
}) {
  const enabled = enabledIds
    .map((id) => getConnector(id))
    .filter((connector): connector is NonNullable<typeof connector> => connector !== null)
    .slice(0, 4);

  if (enabled.length === 0) {
    return (
      <div className="connector-workbar">
        <button
          type="button"
          className="connector-workbar__empty"
          aria-expanded={expanded}
          onClick={onOpen}
        >
          Connectors
        </button>
      </div>
    );
  }

  return (
    <div className="connector-workbar">
      <button
        type="button"
        className="connector-workbar__cluster"
        onClick={onOpen}
        aria-expanded={expanded}
        aria-label="Connectors"
      >
        <span className="connector-workbar__icons">
          {enabled.map((connector, index) => (
            <span
              key={connector.id}
              className="connector-workbar__icon"
              style={{ zIndex: enabled.length - index }}
            >
              <ConnectorIcon connector={connector} size="xs" />
            </span>
          ))}
        </span>
        Connectors
      </button>
    </div>
  );
}
