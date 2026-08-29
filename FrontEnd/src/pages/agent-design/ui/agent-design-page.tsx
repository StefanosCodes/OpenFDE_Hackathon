import { ArrowLeft, MoreHorizontal } from "lucide-react";
import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAgent, useAgents } from "@/app/providers/agent-provider";
import { toggleConnectorId } from "@/entities/agent/model/agent-state";
import { DesignArtifactPanel } from "@/widgets/design-artifact/ui/design-artifact";
import { DesignChat } from "@/widgets/design-chat/ui/design-chat";

export function AgentDesignPage() {
  const navigate = useNavigate();
  const { agentId } = useParams();
  const { createAgent, addMessage, updateAgentTools, generateArtifact, generateCanvas } =
    useAgents();
  const agent = useAgent(agentId);
  const [draft, setDraft] = React.useState("");
  const [draftConnectors, setDraftConnectors] = React.useState<string[]>([]);
  const [isSending, setIsSending] = React.useState(false);
  const [isGenerating, setIsGenerating] = React.useState(false);

  const enabledConnectorIds = agent?.enabledConnectorIds ?? draftConnectors;

  const toggleConnector = (id: string) => {
    if (isSending || isGenerating) return;
    if (agent) {
      updateAgentTools(agent.id, {
        enabledConnectorIds: toggleConnectorId(agent.enabledConnectorIds, id),
      });
      return;
    }
    setDraftConnectors((current) => toggleConnectorId(current, id));
  };

  const send = async () => {
    const input = draft.trim();
    if (!input || isSending) return;
    setIsSending(true);

    try {
      if (!agentId) {
        const created = await createAgent(input, {
          enabledConnectorIds: draftConnectors,
        });
        if (!created) return;
        setDraft("");
        navigate(`/agents/${created.id}/design`, { replace: true });
        return;
      }

      if (agent) {
        await addMessage(agent.id, input);
        setDraft("");
      }
    } finally {
      setIsSending(false);
    }
  };

  if (agentId && !agent) {
    return (
      <div className="missing-state">
        <h1>Agent not found</h1>
        <button className="button" onClick={() => navigate("/agents")}>
          Return to agents
        </button>
      </div>
    );
  }

  const showBrief = Boolean(agent?.artifact);
  const nextAction = !agent
    ? null
    : agent.artifact
      ? {
          label: "Generate visual map",
          onClick: async () => {
            generateCanvas(agent.id);
            navigate(`/agents/${agent.id}/canvas`);
          },
          disabled: isGenerating,
        }
      : {
          label: "Generate Agent Design",
          onClick: async () => {
            if (isGenerating) return;
            setIsGenerating(true);
            try {
              await generateArtifact(agent.id);
            } finally {
              setIsGenerating(false);
            }
          },
          disabled: isGenerating,
        };

  return (
    <section className="design-page">
      <header className="workspace-header">
        <button
          type="button"
          className="icon-button"
          aria-label="Back to agents"
          onClick={() => navigate("/agents")}
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <strong>{agent?.name ?? "New agent"}</strong>
          <span>{agent ? "In progress" : "Not saved yet"}</span>
        </div>
        <button type="button" className="icon-button workspace-header__more">
          <MoreHorizontal size={18} />
        </button>
      </header>

      <div className={showBrief ? "design-layout" : "design-layout design-layout--chat-only"}>
        <DesignChat
          messages={agent?.messages ?? []}
          draft={draft}
          onDraftChange={setDraft}
          onSend={send}
          enabledConnectorIds={enabledConnectorIds}
          onToggleConnector={toggleConnector}
          nextAction={nextAction}
          isBusy={isSending || isGenerating}
        />
        {agent?.artifact ? (
          <DesignArtifactPanel markdown={agent.artifact.markdown} />
        ) : null}
      </div>
    </section>
  );
}
