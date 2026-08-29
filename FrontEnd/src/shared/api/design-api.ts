import type {
  CanvasDocument,
  ChatMessage,
} from "@/entities/agent/model/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000/v1";

type RequestMessage = Pick<ChatMessage, "role" | "content">;

export type DesignChatResult = {
  assistant_message: string;
  suggested_agent_name: string;
  readiness_score: number;
  missing_information: string[];
  can_generate_design: boolean;
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`OpenFDE API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}
