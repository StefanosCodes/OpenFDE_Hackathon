import { Check, Plus, Search } from "lucide-react";
import * as React from "react";

import {
  connectors,
  type Connector,
} from "@/entities/connector/model/connectors";
import { ConnectorIcon } from "@/entities/connector/ui/connector-icon";

const STORAGE_KEY = "openfde-connected-services-v1";

export function ConnectorsPage() {
  const [query, setQuery] = React.useState("");
  const [connected, setConnected] = React.useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '["github"]') as string[];
    } catch {
      return ["github"];
    }
  });

  React.useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(connected));
    } catch {
      // Local state fallback
    }
  }, [connected]);

  const toggle = (id: string) => {
    setConnected((current) =>
      current.includes(id)
        ? current.filter((connectedId) => connectedId !== id)
        : [...current, id],
    );
  };

  const normalizedQuery = query.trim().toLowerCase();
  const visible = connectors.filter((connector) =>
    `${connector.name} ${connector.description}`
      .toLowerCase()
      .includes(normalizedQuery),
  );

  const featured = visible.filter((connector) => connector.category === "featured");
  const productivity = visible.filter(
    (connector) => connector.category === "productivity",
  );

  return (
    <section className="page connectors-page">
      <div className="page-inner">
        <header className="page-header connectors-header">
          <div>
            <h1>Connectors</h1>
            <p>Give agents access to the tools, knowledge, and codebases they need.</p>
          </div>
          <label className="search-field">
            <Search size={16} className="search-field__icon" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search connectors"
            />
          </label>
        </header>

        <div className="connector-sections">
          {featured.length > 0 ? (
            <ConnectorSection title="Featured">
              {featured.map((connector) => (
                <ConnectorRow
                  key={connector.id}
                  connector={connector}
                  isConnected={connected.includes(connector.id)}
                  onToggle={() => toggle(connector.id)}
                />
              ))}
            </ConnectorSection>
          ) : null}

          {productivity.length > 0 ? (
            <ConnectorSection title="Productivity">
              {productivity.map((connector) => (
                <ConnectorRow
                  key={connector.id}
                  connector={connector}
                  isConnected={connected.includes(connector.id)}
                  onToggle={() => toggle(connector.id)}
                />
              ))}
            </ConnectorSection>
          ) : null}
        </div>

        {visible.length === 0 ? (
          <div className="no-results">No connectors match “{query}”.</div>
        ) : null}
      </div>
    </section>
  );
}

function ConnectorSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="connector-section">
      <h2 className="connector-section__title">{title}</h2>
      <div className="connector-section__grid">{children}</div>
    </div>
  );
}

function ConnectorRow({
  connector,
  isConnected,
  onToggle,
}: {
  connector: Connector;
  isConnected: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="connector-row">
      <button
        type="button"
        className="connector-row__content"
        onClick={onToggle}
      >
        <ConnectorIcon connector={connector} size="md" />
        <div className="connector-row__info">
          <span className="connector-row__name">{connector.name}</span>
          <span className="connector-row__description">
            {connector.description}
          </span>
        </div>
      </button>
      <button
        type="button"
        className={`connector-action ${isConnected ? "connector-action--connected" : ""}`}
        onClick={onToggle}
        aria-label={isConnected ? `Disconnect ${connector.name}` : `Connect ${connector.name}`}
      >
        {isConnected ? <Check size={14} /> : <Plus size={14} />}
        <span>{isConnected ? "Connected" : "Connect"}</span>
      </button>
    </div>
  );
}
