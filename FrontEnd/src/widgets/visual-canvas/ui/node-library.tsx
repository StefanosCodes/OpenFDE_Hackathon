import {
  BookOpen,
  CheckCircle2,
  GitBranch,
  MessageCircle,
  Play,
  Plus,
  Zap,
} from "lucide-react";

import type { CanvasNodeData, CanvasNodeKind } from "@/entities/agent/model/types";

const nodeTemplates: Array<{
  kind: CanvasNodeKind;
  label: string;
  description: string;
  icon: typeof Play;
}> = [
  {
    kind: "start",
    label: "Start",
    description: "A person begins",
    icon: Play,
  },
  {
    kind: "message",
    label: "Talk",
    description: "Say or ask something",
    icon: MessageCircle,
  },
  {
    kind: "knowledge",
    label: "Knowledge",
    description: "Find trusted information",
    icon: BookOpen,
  },
  {
    kind: "decision",
    label: "Choose a path",
    description: "Make a simple decision",
    icon: GitBranch,
  },
  {
    kind: "action",
    label: "Take action",
    description: "Use a connector",
    icon: Zap,
  },
  {
    kind: "finish",
    label: "Finish",
    description: "Give the result",
    icon: CheckCircle2,
  },
];

export function NodeLibrary({
  onAdd,
}: {
  onAdd: (data: CanvasNodeData) => void;
}) {
  return (
    <aside className="node-library">
      <div className="node-library__heading">
        <span>
          <strong>Building blocks</strong>
          <small>Click to add</small>
        </span>
        <Plus size={16} />
      </div>
      <div className="node-library__list">
        {nodeTemplates.map((template) => {
          const Icon = template.icon;
          return (
            <button
              type="button"
              key={template.kind}
              onClick={() =>
                onAdd({
                  kind: template.kind,
                  label: template.label,
                  description: template.description,
                })
              }
            >
              <span data-kind={template.kind}>
                <Icon size={16} />
              </span>
              <span>
                <strong>{template.label}</strong>
                <small>{template.description}</small>
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
