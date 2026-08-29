export type GitHubRepository = {
  id: number;
  full_name: string;
  private: boolean;
  default_branch: string;
};

export type GitHubConnection = {
  status: "disconnected" | "connecting" | "awaiting_repository" | "connected" | "error";
  account_login: string | null;
  repository: GitHubRepository | null;
  last_error: string | null;
  updated_at: string | null;
};

type GitHubConnectResponse = {
  status: "connecting";
  connect_url: string;
  expires_in_seconds: number;
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001").replace(/\/$/, "");
const DEMO_AUTH_TOKEN = import.meta.env.VITE_DEMO_AUTH_TOKEN ?? "user-a";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/v1${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${DEMO_AUTH_TOKEN}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as {
        detail?: string | { message?: string; reason?: string };
      };
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (payload.detail?.message) {
        message = payload.detail.reason
          ? `${payload.detail.message}: ${payload.detail.reason}`
          : payload.detail.message;
      }
    } catch {
      // Keep the HTTP status fallback for non-JSON responses.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const githubConnectorApi = {
  status: () => request<GitHubConnection>("/connectors/github"),
  connect: (returnMode: "page" | "popup") =>
    request<GitHubConnectResponse>(
      `/connectors/github/connect?return_mode=${returnMode}`,
      { method: "POST" },
    ),
  repositories: () => request<GitHubRepository[]>("/connectors/github/repositories"),
  selectRepository: (repositoryId: number) =>
    request<GitHubConnection>("/connectors/github/repository", {
      method: "PUT",
      body: JSON.stringify({ repository_id: repositoryId }),
    }),
  disconnect: () => request<GitHubConnection>("/connectors/github", { method: "DELETE" }),
};
