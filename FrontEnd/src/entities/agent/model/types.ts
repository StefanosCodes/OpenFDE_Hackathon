import type { Edge, Node } from "@xyflow/react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
};

export type DesignArtifact = {
  id: string;
  markdown: string;
  createdAt: number;
};

export type CanvasNodeKind =
  | "start"
  | "message"
  | "knowledge"
  | "decision"
  | "action"
  | "finish";

export type CanvasNodeData = Record<string, unknown> & {
  label: string;
  description: string;
  kind: CanvasNodeKind;
};

export type CanvasNode = Node<CanvasNodeData, "journey">;

export type CanvasEdge = Edge;

export type CanvasDocument = {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  createdAt: number;
};

export type Agent = {
  id: string;
  name: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  enabledConnectorIds: string[];
  skillId: string | null;
  proposedCanvas?: CanvasDocument;
  readinessScore?: number;
  missingInformation?: string[];
  canGenerateDesign?: boolean;
  mermaid?: string;
  knowledgeSources?: unknown[];
  intents?: unknown[];
  datasets?: unknown[];
  datasetExports?: Record<string, string>;
  modelError?: string | null;
  artifact?: DesignArtifact;
  canvas?: CanvasDocument;
  submittedAt?: number;
};

export type AgentStage =
  | "In progress"
  | "Brief ready"
  | "Canvas ready"
  | "Submitted";
