import { ArrowRight } from "lucide-react";

import type { ChatMessage } from "@/entities/agent/model/types";
import { ChatComposer } from "@/features/agent-chat/ui/chat-composer";

const suggestions = [
  "Create an onboarding agent for new customers",
  "Help support teams answer product questions",
  "Build an agent that qualifies sales leads",
];

export function DesignChat({
  messages,
  draft,
  onDraftChange,
  onSend,
  enabledConnectorIds,
  onToggleConnector,
  nextAction,
  isBusy = false,
}: {
  messages: ChatMessage[];
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  enabledConnectorIds: string[];
  onToggleConnector: (id: string) => void;
  nextAction?: { label: string; onClick: () => void; disabled?: boolean } | null;
  isBusy?: boolean;
}) {
  const isEmpty = messages.length === 0;
  const composer = (
    <ChatComposer
      value={draft}
      onChange={onDraftChange}
      onSubmit={onSend}
      enabledConnectorIds={enabledConnectorIds}
      onToggleConnector={onToggleConnector}
      disabled={isBusy}
    />
  );

  return (
    <div className="design-chat">
      <div className={isEmpty ? "chat-thread chat-thread--empty" : "chat-thread"}>
        {isEmpty ? (
          <div className="chat-empty">
            <h1>What should your agent do?</h1>
            <div className="empty-composer">{composer}</div>
            <div className="suggestion-list">
              {suggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion}
                  onClick={() => onDraftChange(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}
      </div>
      {isEmpty ? (
        <p className="chat-disclaimer">
          OpenFDE can make mistakes. Review important details.
        </p>
      ) : (
        <div className="composer-dock">
          {nextAction ? (
            <div className="composer-next-action">
              <button
                type="button"
                className="composer-next-action__button"
                onClick={nextAction.onClick}
                disabled={isBusy || nextAction.disabled}
              >
                {isBusy && nextAction.disabled ? "Working..." : nextAction.label}
                <ArrowRight size={15} />
              </button>
            </div>
          ) : null}
          {composer}
          <p>OpenFDE can make mistakes. Review important details.</p>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return <div className="message message--user">{message.content}</div>;
  }

  return (
    <div className="message message--assistant">
      <p>{message.content}</p>
    </div>
  );
}
