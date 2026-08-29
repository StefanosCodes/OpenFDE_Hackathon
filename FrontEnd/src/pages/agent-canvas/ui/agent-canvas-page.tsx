import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  type NodeTypes,
} from "@xyflow/react";
import { useParams } from "react-router-dom";

import { useAgent } from "@/app/providers/agent-provider";
import { JourneyNode } from "@/widgets/visual-canvas/ui/journey-node";

const nodeTypes: NodeTypes = { journey: JourneyNode };

export function AgentCanvasPage() {
  const { agentId } = useParams();
  const agent = useAgent(agentId);

  if (!agent?.canvas) return null;

  return (
    <div className="canvas-workspace">
      <ReactFlow
        nodes={agent.canvas.nodes}
        edges={agent.canvas.edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        edgesReconnectable={false}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        defaultEdgeOptions={{ type: "smoothstep", animated: false }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.35}
        maxZoom={1.5}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          size={1.3}
          color="var(--border)"
        />
        <Controls position="bottom-left" showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
