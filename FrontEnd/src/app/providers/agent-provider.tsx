import * as React from "react";

import {
  addConversationTurn,
  applyGeneratedCanvas,
  createAgentFromPrompt,
  createDesignArtifact,
  deleteAgent as removeAgentFromList,
  markAgentSubmitted,
} from "@/entities/agent/model/agent-state";
import type { Agent, CanvasDocument } from "@/entities/agent/model/types";

const STORAGE_KEY = "openfde-agent-builder-v1";

type AgentTools = {
  enabledConnectorIds?: string[];
  skillId?: string | null;
};

type AgentContextValue = {
  agents: Agent[];
  createAgent: (prompt: string, extras?: AgentTools) => Agent | null;
  deleteAgent: (agentId: string) => void;
  addMessage: (agentId: string, prompt: string) => void;
  updateAgentTools: (agentId: string, tools: AgentTools) => void;
  generateArtifact: (agentId: string) => void;
  generateCanvas: (agentId: string) => void;
  updateCanvas: (agentId: string, canvas: CanvasDocument) => void;
  submitAgent: (agentId: string) => void;
};

const AgentContext = React.createContext<AgentContextValue | null>(null);

function normalizeAgent(value: unknown): Agent | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Agent;
  if (typeof record.id !== "string" || typeof record.name !== "string") {
    return null;
  }
  return {
    ...record,
    enabledConnectorIds: Array.isArray(record.enabledConnectorIds)
      ? record.enabledConnectorIds.filter((id) => typeof id === "string")
      : [],
    skillId: typeof record.skillId === "string" ? record.skillId : null,
    submittedAt:
      typeof record.submittedAt === "number" ? record.submittedAt : undefined,
  };
}

function readAgents(): Agent[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed: unknown = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(normalizeAgent)
      .filter((agent): agent is Agent => agent !== null);
  } catch {
    return [];
  }
}

export function AgentProvider({ children }: { children: React.ReactNode }) {
  const [agents, setAgents] = React.useState<Agent[]>(readAgents);

  React.useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(agents));
    } catch {
      // The prototype remains usable when browser storage is unavailable.
    }
  }, [agents]);

  const createAgent = React.useCallback((prompt: string, extras?: AgentTools) => {
    const agent = createAgentFromPrompt(
      prompt,
      () => crypto.randomUUID(),
      Date.now(),
      extras,
    );
    if (!agent) return null;
    setAgents((current) => [agent, ...current]);
    return agent;
  }, []);

  const deleteAgent = React.useCallback((agentId: string) => {
    setAgents((current) => removeAgentFromList(current, agentId));
  }, []);

  const changeAgent = React.useCallback(
    (agentId: string, change: (agent: Agent) => Agent) => {
      setAgents((current) =>
        current.map((agent) => (agent.id === agentId ? change(agent) : agent)),
      );
    },
    [],
  );

  const addMessage = React.useCallback(
    (agentId: string, prompt: string) => {
      changeAgent(agentId, (agent) => addConversationTurn(agent, prompt));
    },
    [changeAgent],
  );

  const updateAgentTools = React.useCallback(
    (agentId: string, tools: AgentTools) => {
      changeAgent(agentId, (agent) => ({
        ...agent,
        enabledConnectorIds:
          tools.enabledConnectorIds ?? agent.enabledConnectorIds,
        skillId: tools.skillId === undefined ? agent.skillId : tools.skillId,
        updatedAt: Date.now(),
      }));
    },
    [changeAgent],
  );

  const generateArtifact = React.useCallback(
    (agentId: string) => {
      changeAgent(agentId, (agent) => ({
        ...agent,
        artifact: createDesignArtifact(agent),
        updatedAt: Date.now(),
      }));
    },
    [changeAgent],
  );

  const generateCanvas = React.useCallback(
    (agentId: string) => {
      changeAgent(agentId, (agent) => applyGeneratedCanvas(agent));
    },
    [changeAgent],
  );

  const submitAgent = React.useCallback(
    (agentId: string) => {
      changeAgent(agentId, (agent) => markAgentSubmitted(agent));
    },
    [changeAgent],
  );

  const updateCanvas = React.useCallback(
    (agentId: string, canvas: CanvasDocument) => {
      changeAgent(agentId, (agent) => ({
        ...agent,
        canvas,
        updatedAt: Date.now(),
      }));
    },
    [changeAgent],
  );

  const value = React.useMemo(
    () => ({
      agents,
      createAgent,
      deleteAgent,
      addMessage,
      updateAgentTools,
      generateArtifact,
      generateCanvas,
      updateCanvas,
      submitAgent,
    }),
    [
      agents,
      createAgent,
      deleteAgent,
      addMessage,
      updateAgentTools,
      generateArtifact,
      generateCanvas,
      updateCanvas,
      submitAgent,
    ],
  );

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}

export function useAgents() {
  const context = React.useContext(AgentContext);
  if (!context) throw new Error("useAgents must be used within AgentProvider");
  return context;
}

export function useAgent(agentId: string | undefined) {
  const { agents } = useAgents();
  return agents.find((agent) => agent.id === agentId) ?? null;
}
