import { BookOpen, Database, MessageSquare, Plus } from "lucide-react";
import { useParams } from "react-router-dom";

import { useAgent } from "@/app/providers/agent-provider";

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
  const { agentId } = useParams();
  const agent = useAgent(agentId);
  const copy = emptyCopy[kind];
  const Icon = copy.icon;
  const items =
    kind === "knowledge"
      ? agent?.knowledgeSources
      : kind === "intents"
        ? agent?.intents
        : agent?.datasets;

  if (items?.length) {
    return (
      <section className="workspace-generated">
        <div className="workspace-generated__header">
          <Icon size={20} />
          <div>
            <h2>{generatedTitle[kind]}</h2>
            <p>{generatedDescription[kind]}</p>
          </div>
        </div>
        <div className="workspace-generated__grid">
          {items.map((item, index) => (
            <GeneratedItem
              key={getRecordString(item, "id") || index}
              kind={kind}
              item={item}
            />
          ))}
        </div>
        {kind === "datasets" && agent?.datasetExports ? (
          <div className="workspace-generated__exports">
            {Object.keys(agent.datasetExports).map((key) => (
              <span key={key}>{formatExportName(key)}</span>
            ))}
          </div>
        ) : null}
      </section>
    );
  }

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

const generatedTitle = {
  knowledge: "Knowledge sources",
  intents: "Agent intents",
  datasets: "Evaluation data sets",
} as const;

const generatedDescription = {
  knowledge: "Generated from the design conversation for FDE implementation.",
  intents: "Core jobs, triggers, tools, and success criteria.",
  datasets: "Seed eval cases and export formats for validation.",
} as const;

function GeneratedItem({
  kind,
  item,
}: {
  kind: keyof typeof emptyCopy;
  item: unknown;
}) {
  const title =
    getRecordString(item, "title") ||
    getRecordString(item, "name") ||
    getRecordString(item, "input") ||
    "Generated item";
  const description =
    getRecordString(item, "description") ||
    getRecordString(item, "trigger") ||
    getRecordString(item, "expected_output") ||
    getRecordString(item, "expected_outcome") ||
    "";
  const primaryTag =
    getRecordString(item, "source_type") ||
    getRecordMetadataString(item, "category") ||
    (kind === "datasets" ? "eval case" : kind.slice(0, -1));
  const secondaryTag =
    getRecordMetadataString(item, "difficulty") ||
    getRecordMetadataString(item, "priority") ||
    (getRecordBoolean(item, "required") ? "required" : "");
  const list =
    kind === "intents"
      ? getRecordStringList(item, "success_criteria")
      : kind === "datasets"
        ? getRecordStringList(item, "expected_tools")
        : [];

  return (
    <article className="workspace-generated__item">
      <div>
        <h3>{title}</h3>
        {description ? <p>{description}</p> : null}
      </div>
      <div className="workspace-generated__tags">
        {primaryTag ? <span>{primaryTag}</span> : null}
        {secondaryTag ? <span>{secondaryTag}</span> : null}
      </div>
      {list.length ? (
        <ul>
          {list.slice(0, 3).map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : null;
}

function getRecordString(value: unknown, key: string) {
  const record = asRecord(value);
  const field = record?.[key];
  return typeof field === "string" ? field : "";
}

function getRecordBoolean(value: unknown, key: string) {
  const record = asRecord(value);
  return record?.[key] === true;
}

function getRecordMetadataString(value: unknown, key: string) {
  const metadata = asRecord(asRecord(value)?.metadata);
  const field = metadata?.[key];
  return typeof field === "string" ? field : "";
}

function getRecordStringList(value: unknown, key: string) {
  const record = asRecord(value);
  const field = record?.[key];
  return Array.isArray(field)
    ? field.filter((item): item is string => typeof item === "string")
    : [];
}

function formatExportName(key: string) {
  return key.replace(/_/g, " ");
}
