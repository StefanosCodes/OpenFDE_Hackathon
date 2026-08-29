import { Bot, ChevronDown, X } from "lucide-react";
import * as React from "react";

import type { Agent } from "@/entities/agent/model/types";
import { ChatComposer } from "@/features/agent-chat/ui/chat-composer";
import { OpenFDEMark } from "@/widgets/app-sidebar/ui/openfde-mark";

export function CanvasChat({
  agent,
  onSend,
}: {
  agent: Agent;
  onSend: (message: string) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [draft, setDraft] = React.useState("");
  const recentMessages = agent.messages.slice(-6);

  const submit = () => {
    const message = draft.trim();
    if (!message) return;
    onSend(message);
    setDraft("");
  };

  if (!open) {
    return (
      <button
        type="button"
        className="canvas-chat-launcher"
        aria-label="Ask your agent"
        onClick={() => setOpen(true)}
      >
        <OpenFDEMark className="canvas-chat-launcher__mark" />
      </button>
    );
  }

  return (
    <aside className="canvas-chat" aria-label="Agent chat">
      <header>
        <span className="assistant-mark">
          <Bot size={16} />
        </span>
        <span>
          <strong>Design assistant</strong>
          <small>Ask about this agent</small>
        </span>
        <button
          type="button"
          className="icon-button"
          aria-label="Close chat"
          onClick={() => setOpen(false)}
        >
          <X size={16} />
        </button>
      </header>
      <div className="canvas-chat__messages">
        {recentMessages.map((message) => (
          <p key={message.id} className={`canvas-message canvas-message--${message.role}`}>
            {message.content}
          </p>
        ))}
        <button type="button" className="chat-history-hint">
          Earlier conversation <ChevronDown size={13} />
        </button>
      </div>
      <ChatComposer
        value={draft}
        onChange={setDraft}
        onSubmit={submit}
        placeholder="Ask about this agent"
        showConnectors={false}
        enabledConnectorIds={agent.enabledConnectorIds}
        onToggleConnector={() => undefined}
      />
    </aside>
  );
}
