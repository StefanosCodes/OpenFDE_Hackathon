import { ArrowLeft } from "lucide-react";
import * as React from "react";
import { Outlet, useMatch, useNavigate, useParams } from "react-router-dom";

import { useAgent, useAgents } from "@/app/providers/agent-provider";
import { ConfirmDialog } from "@/shared/ui/confirm-dialog";
import { AgentWorkspaceSidebar } from "@/widgets/agent-workspace-sidebar/ui/agent-workspace-sidebar";
import { CanvasChat } from "@/widgets/canvas-chat/ui/canvas-chat";

export function AgentWorkspaceLayout() {
  const navigate = useNavigate();
  const params = useParams();
  const workspaceMatch = useMatch("/agents/:agentId/*");
  const agentId = params.agentId ?? workspaceMatch?.params.agentId;
  const { addMessage, submitAgent } = useAgents();
  const agent = useAgent(agentId);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  React.useEffect(() => {
    if (!agentId || !agent) {
      navigate("/agents", { replace: true });
      return;
    }
    if (!agent.canvas) {
      navigate(`/agents/${agent.id}/design`, { replace: true });
    }
  }, [agent, agentId, navigate]);

  if (!agent?.canvas) return null;

  const submitted = Boolean(agent.submittedAt);

  return (
    <div className="app-shell">
      <AgentWorkspaceSidebar agentId={agent.id} />
      <main className="app-main">
        <header className="workspace-header">
          <button
            type="button"
            className="icon-button"
            aria-label="Back to design brief"
            onClick={() => navigate(`/agents/${agent.id}/design`)}
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <strong>{agent.name}</strong>
          </div>
          <div className="canvas-header__actions">
            <button
              type="button"
              className="button button--primary"
              disabled={submitted}
              onClick={() => setConfirmOpen(true)}
            >
              {submitted ? "Submitted" : "Submit Agent"}
            </button>
          </div>
        </header>
        <div className="workspace-body">
          <Outlet />
          <CanvasChat
            agent={agent}
            onSend={(message) => addMessage(agent.id, message)}
          />
        </div>
      </main>
      <ConfirmDialog
        open={confirmOpen}
        title="Submit agent"
        description={`Submit “${agent.name}”? It will be marked Submitted. You can still view the map and talk to it.`}
        confirmLabel="Submit"
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => submitAgent(agent.id)}
      />
    </div>
  );
}
