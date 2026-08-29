import { BookOpen, Database, MessageSquare, Plus } from "lucide-react";

const emptyCopy = {
  knowledge: {
    icon: BookOpen,
    title: "No sources yet",
    description:
      "Attach the documents and URLs this agent should trust. Nothing is connected in this prototype.",
    action: "Add knowledge",
  },
  intents: {
    icon: MessageSquare,
    title: "No intents yet",
    description:
      "Intents will describe the jobs this agent can take on. This tab is here so you can walk the workspace.",
    action: "Add intent",
  },
  datasets: {
    icon: Database,
    title: "No data sets yet",
    description:
      "Data sets will live here when this agent needs structured tables. This tab is empty on purpose.",
    action: "Add data set",
  },
} as const;

export function WorkspaceEmptyPage({
  kind,
}: {
  kind: keyof typeof emptyCopy;
}) {
  const copy = emptyCopy[kind];
  const Icon = copy.icon;

  return (
    <div className="workspace-empty">
      <div className="artifact-empty">
        <Icon size={23} />
        <h2>{copy.title}</h2>
        <p>{copy.description}</p>
        <button type="button" className="button button--primary">
          <Plus size={16} />
          {copy.action}
        </button>
      </div>
    </div>
  );
}
