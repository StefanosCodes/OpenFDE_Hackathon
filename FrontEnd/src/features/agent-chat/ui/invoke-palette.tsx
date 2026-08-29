import { Link } from "react-router-dom";

import { connectors, type Connector } from "@/entities/connector/model/connectors";
import { ConnectorIcon } from "@/entities/connector/ui/connector-icon";

export function InvokePalette({
  query,
  enabledIds,
  onToggle,
}: {
  query: string;
  enabledIds: string[];
  onToggle: (id: string) => void;
}) {
  const normalized = query.trim().toLowerCase();
  const visible = connectors.filter((connector) =>
    `${connector.name} ${connector.description}`
      .toLowerCase()
      .includes(normalized),
  );

  return (
    <div className="invoke-palette" role="listbox" aria-label="Connectors">
      <div className="invoke-palette__list">
        {visible.length === 0 ? (
          <p className="invoke-palette__empty">No matching connectors</p>
        ) : (
          visible.map((connector) => (
            <ConnectorRow
              key={connector.id}
              connector={connector}
              connected={enabledIds.includes(connector.id)}
              onToggle={() => onToggle(connector.id)}
            />
          ))
        )}
      </div>
      <div className="invoke-palette__footer">
        <Link to="/connectors">Browse all connectors</Link>
      </div>
    </div>
  );
}

function ConnectorRow({
  connector,
  connected,
  onToggle,
}: {
  connector: Connector;
  connected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className="invoke-palette__row"
      role="option"
      aria-selected={connected}
      onClick={onToggle}
    >
      <ConnectorIcon connector={connector} size="xs" />
      <span className="invoke-palette__title">{connector.name}</span>
      {connected ? (
        <span className="invoke-palette__status">Connected</span>
      ) : (
        <span className="invoke-palette__add" aria-hidden>
          +
        </span>
      )}
    </button>
  );
}
