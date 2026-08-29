import {
  BookOpen,
  Bot,
  CheckCircle2,
  GitBranch,
  MessageCircle,
  Play,
  Zap,
} from "lucide-react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

import type { CanvasNode, CanvasNodeKind } from "@/entities/agent/model/types";

const kindIcons = {
  start: Play,
  message: MessageCircle,
  knowledge: BookOpen,
  decision: GitBranch,
  action: Zap,
  finish: CheckCircle2,
} satisfies Record<CanvasNodeKind, typeof Bot>;

export function JourneyNode({ data, selected }: NodeProps<CanvasNode>) {
  const Icon = kindIcons[data.kind];
  return (
    <div
      className={selected ? "journey-node journey-node--selected" : "journey-node"}
      data-kind={data.kind}
    >
      <Handle type="target" position={Position.Left} />
      <span className="journey-node__icon">
        <Icon size={18} />
      </span>
      <span>
        <strong>{data.label}</strong>
        <small>{data.description}</small>
      </span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
