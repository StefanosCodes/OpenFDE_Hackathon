import * as React from "react";

import {
  addConversationTurn,
  applyDesignArtifact,
  applyGeneratedCanvas,
  createAgentFromPrompt,
  createDesignArtifact,
  deleteAgent as removeAgentFromList,
  markAgentSubmitted,
} from "@/entities/agent/model/agent-state";
import type { Agent, CanvasDocument } from "@/entities/agent/model/types";
import {
  requestDesignArtifact,
  requestDesignChat,
} from "@/shared/api/design-api";

const STORAGE_KEY = "openfde-agent-builder-v1";

type AgentTools = {
  enabledConnectorIds?: string[];
  skillId?: string | null;
};

type AgentContextValue = {
  agents: Agent[];
  createAgent: (prompt: string, extras?: AgentTools) => Promise<Agent | null>;
  deleteAgent: (agentId: string) => void;
  addMessage: (agentId: string, prompt: string) => Promise<void>;
  updateAgentTools: (agentId: string, tools: AgentTools) => void;
  generateArtifact: (agentId: string) => Promise<void>;
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

  const createAgent = React.useCallback(async (prompt: string, extras?: AgentTools) => {
    const trimmed = prompt.trim();
    if (!trimmed) return null;

    let agent: Agent | null;
    try {
      const response = await requestDesignChat({
        agent_name: null,
        messages: [{ role: "user", content: trimmed }],
        enabled_connector_ids: extras?.enabledConnectorIds ?? [],
        skill_id: extras?.skillId ?? null,
      });
      agent = createAgentFromPrompt(
        trimmed,
        () => crypto.randomUUID(),
        Date.now(),
        {
          ...extras,
          assistantMessage: response.assistant_message,
          suggestedAgentName: response.suggested_agent_name,
          readinessScore: response.readiness_score,
          missingInformation: response.missing_information,
          canGenerateDesign: response.can_generate_design,
        },
      );
    } catch {
      agent = createAgentFromPrompt(
        trimmed,
        () => crypto.randomUUID(),
        Date.now(),
        {
          ...extras,
          modelError: "Live model request failed; using local draft mode.",
        },
      );
    }

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
    async (agentId: string, prompt: string) => {
      const agent = agents.find((item) => item.id === agentId);
      const trimmed = prompt.trim();
      if (!agent || !trimmed) return;

      const messages = [
        ...agent.messages.map(({ role, content }) => ({ role, content })),
        { role: "user" as const, content: trimmed },
      ];

      try {
        const response = await requestDesignChat({
          agent_name: agent.name,
          messages,
          enabled_connector_ids: agent.enabledConnectorIds,
          skill_id: agent.skillId,
        });
        changeAgent(agentId, (current) =>
          addConversationTurn(
            current,
            trimmed,
            () => crypto.randomUUID(),
            Date.now(),
            response.assistant_message,
            {
              suggestedAgentName: response.suggested_agent_name,
              readinessScore: response.readiness_score,
              missingInformation: response.missing_information,
              canGenerateDesign: response.can_generate_design,
            },
          ),
        );
      } catch {
        changeAgent(agentId, (current) =>
          addConversationTurn(current, trimmed, undefined, undefined, undefined, {
            modelError: "Live model request failed; using local draft mode.",
          }),
        );
      }
    },
    [agents, changeAgent],
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
    async (agentId: string) => {
      const agent = agents.find((item) => item.id === agentId);
      if (!agent) return;

      try {
        const response = await requestDesignArtifact({
          agent_name: agent.name,
          messages: agent.messages.map(({ role, content }) => ({ role, content })),
          enabled_connector_ids: agent.enabledConnectorIds,
          skill_id: agent.skillId,
        });
        changeAgent(agentId, (current) =>
          applyDesignArtifact(
            current,
            {
              agentName: response.agent_name,
              markdown: response.markdown,
              canvas: response.canvas,
              mermaid: response.mermaid,
              knowledgeSources: response.knowledge_sources,
              intents: response.intents,
              datasets: response.datasets,
              datasetExports: response.dataset_exports,
            },
            () => crypto.randomUUID(),
            Date.now(),
          ),
        );
      } catch {
        changeAgent(agentId, (agent) => ({
          ...agent,
          artifact: createDesignArtifact(agent),
          modelError: "Live artifact request failed; using local draft mode.",
          updatedAt: Date.now(),
        }));
      }
    },
    [agents, changeAgent],
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
