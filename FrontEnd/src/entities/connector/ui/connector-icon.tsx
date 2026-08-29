import type { Connector } from "@/entities/connector/model/connectors";

export type ConnectorIconSize = "xs" | "sm" | "md" | "lg";

const SIZE_CLASS: Record<ConnectorIconSize, string> = {
  xs: "connector-icon--xs",
  sm: "connector-icon--sm",
  md: "connector-icon--md",
  lg: "connector-icon--lg",
};

export function ConnectorIcon({
  connector,
  size = "md",
  className = "",
}: {
  connector: Connector;
  size?: ConnectorIconSize;
  className?: string;
}) {
  return (
    <span
      className={`connector-icon ${SIZE_CLASS[size]} ${className}`.trim()}
      aria-hidden="true"
    >
      <img
        src={connector.icon}
        alt=""
        className="connector-icon__img"
        draggable={false}
      />
    </span>
  );
}
