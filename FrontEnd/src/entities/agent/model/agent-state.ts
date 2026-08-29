import type {
  Agent,
  AgentStage,
  CanvasDocument,
  ChatMessage,
  DesignArtifact,
} from "@/entities/agent/model/types";

type IdFactory = () => string;

type DiscoveryMetadata = {
  suggestedAgentName?: string;
  readinessScore?: number;
  missingInformation?: string[];
  canGenerateDesign?: boolean;
  modelError?: string | null;
};

type CreateAgentExtras = {
  enabledConnectorIds?: string[];
  skillId?: string | null;
  assistantMessage?: string;
} & DiscoveryMetadata;

type DesignArtifactResult = {
  agentName: string;
  markdown: string;
  canvas: CanvasDocument;
  mermaid?: string;
  knowledgeSources?: unknown[];
  intents?: unknown[];
  datasets?: unknown[];
  datasetExports?: Record<string, string>;
};

export function deriveAgentName(input: string) {
  const trimmed = input.trim().replace(/\s+/g, " ");
  if (!trimmed) return "Untitled agent";
  return trimmed.length > 42 ? `${trimmed.slice(0, 42)}…` : trimmed;
}

export function createAgentFromPrompt(
  rawPrompt: string,
  makeId: IdFactory = () => crypto.randomUUID(),
  now = Date.now(),
  extras: CreateAgentExtras = {},
): Agent | null {
  const prompt = rawPrompt.trim();
  if (!prompt) return null;
  const assistantMessage =
    extras.assistantMessage ??
    "Great — I started this agent. Tell me who it helps, what it should do, and what a successful result looks like. When the idea feels right, we can turn it into a design brief.";

  return {
    id: makeId(),
    name: extras.suggestedAgentName?.trim() || deriveAgentName(prompt),
    createdAt: now,
    updatedAt: now,
    enabledConnectorIds: extras.enabledConnectorIds ?? [],
    skillId: extras.skillId ?? null,
    readinessScore: extras.readinessScore,
    missingInformation: extras.missingInformation,
    canGenerateDesign: extras.canGenerateDesign,
    modelError: extras.modelError ?? null,
    messages: [
      createMessage("user", prompt, makeId, now),
      createMessage("assistant", assistantMessage, makeId, now),
    ],
  };
}

export function toggleConnectorId(ids: string[], connectorId: string) {
  return ids.includes(connectorId)
    ? ids.filter((id) => id !== connectorId)
    : [...ids, connectorId];
}

export function addConversationTurn(
  agent: Agent,
  rawPrompt: string,
  makeId: IdFactory = () => crypto.randomUUID(),
  now = Date.now(),
  assistantMessage?: string,
  metadata: DiscoveryMetadata = {},
): Agent {
  const prompt = rawPrompt.trim();
  if (!prompt) return agent;

  const answer =
    assistantMessage ??
    (agent.canvas
      ? "I’ve added that to our conversation. The map stays unchanged until you choose to apply a suggested edit."
      : "That helps. I’m shaping the goal, audience, knowledge, actions, and boundaries into a simple plan. Add anything else that matters, or create the design brief when you’re ready.");

  return {
    ...agent,
    name: metadata.suggestedAgentName?.trim() || agent.name,
    readinessScore: metadata.readinessScore ?? agent.readinessScore,
    missingInformation: metadata.missingInformation ?? agent.missingInformation,
    canGenerateDesign: metadata.canGenerateDesign ?? agent.canGenerateDesign,
    modelError: metadata.modelError ?? null,
    updatedAt: now,
    messages: [
      ...agent.messages,
      createMessage("user", prompt, makeId, now),
      createMessage("assistant", answer, makeId, now),
    ],
  };
}

export function applyDesignArtifact(
  agent: Agent,
  result: DesignArtifactResult,
  makeId: IdFactory = () => crypto.randomUUID(),
  now = Date.now(),
): Agent {
  return {
    ...agent,
    name: result.agentName || agent.name,
    artifact: {
      id: makeId(),
      markdown: result.markdown,
      createdAt: now,
    },
    proposedCanvas: result.canvas,
    mermaid: result.mermaid,
    knowledgeSources: result.knowledgeSources,
    intents: result.intents,
    datasets: result.datasets,
    datasetExports: result.datasetExports,
    modelError: null,
    updatedAt: now,
  };
}

export function createDesignArtifact(
  agent: Agent,
  makeId: IdFactory = () => crypto.randomUUID(),
  now = Date.now(),
): DesignArtifact {
  const firstPrompt =
    agent.messages.find((message) => message.role === "user")?.content ??
    "Help people complete a useful task.";

  return {
    id: makeId(),
    createdAt: now,
    markdown: `# ${agent.name}

## Purpose
${firstPrompt}

## Experience
The agent starts with a friendly conversation, understands what the person needs, uses the right knowledge or connector, and gives a clear result.

## Knowledge
Use only sources connected to this agent. Explain when information is missing instead of guessing.

## Actions
- Understand the request
- Find the relevant information
- Complete the requested task
- Confirm the result in plain language

## Guardrails
- Ask before taking consequential actions
- Keep private information scoped to this agent
- Let the person know when human help is needed`,
  };
}

export function createCanvasDocument(
  makeId: IdFactory = () => crypto.randomUUID(),
  now = Date.now(),
): CanvasDocument {
  const startId = makeId();
  const understandId = makeId();
  const knowledgeId = makeId();
  const finishId = makeId();

  return {
    createdAt: now,
    nodes: [
      {
        id: startId,
        type: "journey",
        position: { x: 40, y: 180 },
        data: {
          kind: "start",
          label: "Person asks",
          description: "A conversation begins",
        },
      },
      {
        id: understandId,
        type: "journey",
        position: { x: 310, y: 180 },
        data: {
          kind: "message",
          label: "Understand",
          description: "Learn what they need",
        },
      },
      {
        id: knowledgeId,
        type: "journey",
        position: { x: 580, y: 180 },
        data: {
          kind: "knowledge",
          label: "Use knowledge",
          description: "Find trusted information",
        },
      },
      {
        id: finishId,
        type: "journey",
        position: { x: 850, y: 180 },
        data: {
          kind: "finish",
          label: "Give a result",
          description: "Respond clearly",
        },
      },
    ],
    edges: [
      { id: `${startId}-${understandId}`, source: startId, target: understandId },
      {
        id: `${understandId}-${knowledgeId}`,
        source: understandId,
        target: knowledgeId,
      },
      {
        id: `${knowledgeId}-${finishId}`,
        source: knowledgeId,
        target: finishId,
      },
    ],
  };
}

export function getAgentStage(agent: Agent): AgentStage {
  if (agent.submittedAt) return "Submitted";
  if (agent.canvas) return "Canvas ready";
  if (agent.artifact) return "Brief ready";
  return "In progress";
}

export function markAgentSubmitted(agent: Agent, now = Date.now()): Agent {
  if (!agent.canvas || agent.submittedAt) return agent;
  return { ...agent, submittedAt: now, updatedAt: now };
}

export function applyGeneratedCanvas(
  agent: Agent,
  makeId: IdFactory = () => crypto.randomUUID(),
  now = Date.now(),
): Agent {
  return {
    ...agent,
    artifact: agent.artifact ?? createDesignArtifact(agent, makeId, now),
    canvas: agent.proposedCanvas ?? createCanvasDocument(makeId, now),
    submittedAt: undefined,
    updatedAt: now,
  };
}

export function getAgentDestination(agent: Agent) {
  return agent.canvas
    ? `/agents/${agent.id}/canvas`
    : `/agents/${agent.id}/design`;
}

export function deleteAgent(agents: Agent[], agentId: string) {
  return agents.filter((agent) => agent.id !== agentId);
}

function createMessage(
  role: ChatMessage["role"],
  content: string,
  makeId: IdFactory,
  createdAt: number,
): ChatMessage {
  return { id: makeId(), role, content, createdAt };
}
