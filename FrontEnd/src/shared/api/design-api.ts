import type {
  CanvasDocument,
  ChatMessage,
} from "@/entities/agent/model/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8001/v1";

const AUTH_TOKEN = import.meta.env.VITE_DEMO_AUTH_TOKEN ?? "user-a";

type RequestMessage = Pick<ChatMessage, "role" | "content">;

export type DesignChatResult = {
  assistant_message: string;
  suggested_agent_name: string;
  readiness_score: number;
  missing_information: string[];
  can_generate_design: boolean;
  codebase_evidence: CodebaseEvidencePacket | null;
};

export type CodebaseEvidenceReference = {
  path: string;
  start_line: number;
  end_line: number;
  relevance: string;
};

export type CodebaseEvidencePacket = {
  repository: string;
  commit_sha: string;
  summary: string;
  findings: string[];
  references: CodebaseEvidenceReference[];
  files_inspected: string[];
  limitations: string[];
  generated_at: string;
};

export type DesignArtifactResult = {
  agent_name: string;
  markdown: string;
  canvas: CanvasDocument;
  mermaid: string;
  knowledge_sources: unknown[];
  intents: unknown[];
  datasets: unknown[];
  dataset_exports: Record<string, string>;
};

export async function requestDesignChat(body: {
  agent_name?: string | null;
  messages: RequestMessage[];
  enabled_connector_ids: string[];
  skill_id?: string | null;
}) {
  return postJson<DesignChatResult>("/agent-design/chat", body);
}

export async function requestDesignArtifact(body: {
  agent_name: string;
  messages: RequestMessage[];
  enabled_connector_ids: string[];
  skill_id?: string | null;
}) {
  return postJson<DesignArtifactResult>("/agent-design/artifact", body);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${AUTH_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`OpenFDE API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}
