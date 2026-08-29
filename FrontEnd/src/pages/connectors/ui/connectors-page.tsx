import { Check, LoaderCircle, Plus, Search } from "lucide-react";
import * as React from "react";

import {
  githubConnectorApi,
  type GitHubConnection,
  type GitHubRepository,
} from "@/entities/connector/api/github-connector";
import { connectors, type Connector } from "@/entities/connector/model/connectors";
import { ConnectorIcon } from "@/entities/connector/ui/connector-icon";
import { GitHubRepositoryDialog } from "@/pages/connectors/ui/github-repository-dialog";

const STORAGE_KEY = "openfde-connected-services-v1";
const GITHUB_CONNECTION_EVENT_KEY = "openfde-github-connection-event";
const GITHUB_CONNECTION_CHANNEL = "openfde-github-connection";
const DISCONNECTED: GitHubConnection = {
  status: "disconnected",
  account_login: null,
  repository: null,
  last_error: null,
  updated_at: null,
};

export function ConnectorsPage() {
  const [query, setQuery] = React.useState("");
  const [connected, setConnected] = React.useState<string[]>(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as string[];
      return stored.filter((id) => id !== "github");
    } catch {
      return [];
    }
  });
  const [github, setGitHub] = React.useState<GitHubConnection>(DISCONNECTED);
  const [repositories, setRepositories] = React.useState<GitHubRepository[]>([]);
  const [githubLoading, setGitHubLoading] = React.useState(true);
  const [githubSaving, setGitHubSaving] = React.useState(false);
  const [githubError, setGitHubError] = React.useState<string | null>(null);
  const [repositoryDialogOpen, setRepositoryDialogOpen] = React.useState(false);

  const refreshGitHub = React.useCallback(async () => {
    try {
      const connection = await githubConnectorApi.status();
      setGitHub(connection);
      setGitHubError(connection.last_error);
      if (connection.status === "awaiting_repository") {
        const available = await githubConnectorApi.repositories();
        setRepositories(available);
        setRepositoryDialogOpen(true);
      }
    } catch (error) {
      setGitHubError(error instanceof Error ? error.message : "Could not load GitHub status");
    } finally {
      setGitHubLoading(false);
    }
  }, []);

  React.useEffect(() => {
    const refreshFromPopup = () => void refreshGitHub();
    const channel =
      "BroadcastChannel" in window
        ? new BroadcastChannel(GITHUB_CONNECTION_CHANNEL)
        : null;
    if (channel) {
      channel.onmessage = (event) => {
        if (event.data?.type === "github-installed") refreshFromPopup();
      };
    }
    const onStorage = (event: StorageEvent) => {
      if (event.key === GITHUB_CONNECTION_EVENT_KEY) refreshFromPopup();
    };
    window.addEventListener("storage", onStorage);

    const params = new URLSearchParams(window.location.search);
    if (params.get("github") === "installed" && params.get("popup") === "1") {
      channel?.postMessage({ type: "github-installed" });
      try {
        localStorage.setItem(GITHUB_CONNECTION_EVENT_KEY, String(Date.now()));
      } catch {
        // BroadcastChannel remains the primary notification path.
      }
      window.setTimeout(() => window.close(), 150);
    }

    return () => {
      channel?.close();
      window.removeEventListener("storage", onStorage);
    };
  }, [refreshGitHub]);

  React.useEffect(() => {
    void refreshGitHub();
    const onFocus = () => void refreshGitHub();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refreshGitHub]);

  React.useEffect(() => {
    if (github.status !== "connecting") return;
    const interval = window.setInterval(() => void refreshGitHub(), 2500);
    return () => window.clearInterval(interval);
  }, [github.status, refreshGitHub]);

  React.useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(connected));
    } catch {
      // Local state fallback for the remaining prototype connectors.
    }
  }, [connected]);

  const toggleMockConnector = (id: string) => {
    setConnected((current) =>
      current.includes(id)
        ? current.filter((connectedId) => connectedId !== id)
        : [...current, id],
    );
  };

  const connectGitHub = async () => {
    setGitHubError(null);
    setGitHubSaving(true);
    const popup = window.open("about:blank", "_blank");
    if (popup) popup.opener = null;
    try {
      const result = await githubConnectorApi.connect(popup ? "popup" : "page");
      setGitHub((current) => ({ ...current, status: "connecting" }));
      if (popup) {
        popup.location.href = result.connect_url;
      } else {
        window.location.assign(result.connect_url);
      }
    } catch (error) {
      popup?.close();
      setGitHubError(error instanceof Error ? error.message : "Could not connect GitHub");
    } finally {
      setGitHubSaving(false);
    }
  };

  const selectRepository = async (repository: GitHubRepository) => {
    setGitHubSaving(true);
    setGitHubError(null);
    try {
      const connection = await githubConnectorApi.selectRepository(repository.id);
      setGitHub(connection);
      setRepositoryDialogOpen(false);
    } catch (error) {
      setGitHubError(error instanceof Error ? error.message : "Could not select repository");
    } finally {
      setGitHubSaving(false);
    }
  };

  const disconnectGitHub = async () => {
    setGitHubSaving(true);
    setGitHubError(null);
    try {
      setGitHub(await githubConnectorApi.disconnect());
      setRepositories([]);
      setRepositoryDialogOpen(false);
    } catch (error) {
      setGitHubError(error instanceof Error ? error.message : "Could not disconnect GitHub");
    } finally {
      setGitHubSaving(false);
    }
  };

  const normalizedQuery = query.trim().toLowerCase();
  const visible = connectors.filter((connector) =>
    `${connector.name} ${connector.description}`.toLowerCase().includes(normalizedQuery),
  );
  const featured = visible.filter((connector) => connector.category === "featured");
  const productivity = visible.filter((connector) => connector.category === "productivity");

  const renderConnector = (connector: Connector) => {
    if (connector.id === "github") {
      const isConnected = github.status === "connected";
      const isBusy = githubLoading || githubSaving;
      const actionLabel = githubLoading
        ? "Loading"
        : github.status === "connecting"
          ? "Connecting"
          : github.status === "awaiting_repository"
            ? "Choose repo"
            : isConnected
              ? "Disconnect"
              : "Connect";
      const onAction = isConnected
        ? disconnectGitHub
        : github.status === "awaiting_repository"
          ? () => setRepositoryDialogOpen(true)
          : connectGitHub;
      return (
        <ConnectorRow
          key={connector.id}
          connector={connector}
          isConnected={isConnected}
          busy={isBusy}
          actionLabel={actionLabel}
          description={github.repository?.full_name ?? connector.description}
          onToggle={() => void onAction()}
        />
      );
    }
    return (
      <ConnectorRow
        key={connector.id}
        connector={connector}
        isConnected={connected.includes(connector.id)}
        onToggle={() => toggleMockConnector(connector.id)}
      />
    );
  };

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

        {githubError ? <div className="connector-error" role="alert">{githubError}</div> : null}

        <div className="connector-sections">
          {featured.length > 0 ? (
            <ConnectorSection title="Featured">{featured.map(renderConnector)}</ConnectorSection>
          ) : null}
          {productivity.length > 0 ? (
            <ConnectorSection title="Productivity">{productivity.map(renderConnector)}</ConnectorSection>
          ) : null}
        </div>

        {visible.length === 0 ? (
          <div className="no-results">No connectors match “{query}”.</div>
        ) : null}
      </div>

      <GitHubRepositoryDialog
        open={repositoryDialogOpen}
        repositories={repositories}
        accountLogin={github.account_login}
        saving={githubSaving}
        onClose={() => setRepositoryDialogOpen(false)}
        onSelect={(repository) => void selectRepository(repository)}
      />
    </section>
  );
}

function ConnectorSection({ title, children }: { title: string; children: React.ReactNode }) {
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
  busy = false,
  actionLabel,
  description,
  onToggle,
}: {
  connector: Connector;
  isConnected: boolean;
  busy?: boolean;
  actionLabel?: string;
  description?: string;
  onToggle: () => void;
}) {
  return (
    <div className="connector-row">
      <button type="button" className="connector-row__content" onClick={onToggle} disabled={busy}>
        <ConnectorIcon connector={connector} size="md" />
        <div className="connector-row__info">
          <span className="connector-row__name">{connector.name}</span>
          <span className="connector-row__description">{description ?? connector.description}</span>
        </div>
      </button>
      <button
        type="button"
        className={`connector-action ${isConnected ? "connector-action--connected" : ""}`}
        onClick={onToggle}
        disabled={busy}
        aria-label={isConnected ? `Disconnect ${connector.name}` : `Connect ${connector.name}`}
      >
        {busy ? (
          <LoaderCircle className="connector-action__spinner" size={14} />
        ) : isConnected ? (
          <Check size={14} />
        ) : (
          <Plus size={14} />
        )}
        <span>{actionLabel ?? (isConnected ? "Connected" : "Connect")}</span>
      </button>
    </div>
  );
}
