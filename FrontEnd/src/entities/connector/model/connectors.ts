import atlassianIcon from "@/assets/connector-icons/atlassian.svg";
import calendarIcon from "@/assets/connector-icons/googlecalendar.svg";
import driveIcon from "@/assets/connector-icons/googledrive.svg";
import githubIcon from "@/assets/connector-icons/github.svg";
import gmailIcon from "@/assets/connector-icons/gmail.svg";
import notionIcon from "@/assets/connector-icons/notion.svg";
import outlookIcon from "@/assets/connector-icons/microsoftoutlook.svg";
import slackIcon from "@/assets/connector-icons/slack.svg";

export type ConnectorCategory = "featured" | "productivity";

export type Connector = {
  id: string;
  name: string;
  description: string;
  category: ConnectorCategory;
  icon: string;
  tools: string[];
};

export const connectors: Connector[] = [
  {
    id: "github",
    name: "GitHub",
    description: "Inspect codebases, pull requests, issues, and CI.",
    category: "featured",
    icon: githubIcon,
    tools: ["inspect_codebase", "list_pull_requests", "get_issue"],
  },
  {
    id: "slack",
    name: "Slack",
    description: "Read team channels, threads, and workspace conversations.",
    category: "featured",
    icon: slackIcon,
    tools: ["search_messages", "list_channels", "post_message"],
  },
  {
    id: "google-drive",
    name: "Google Drive",
    description: "Work across files, shared folders, and documentation.",
    category: "featured",
    icon: driveIcon,
    tools: ["search_files", "get_file", "read_doc"],
  },
  {
    id: "calendar",
    name: "Google Calendar",
    description: "Check availability, list events, and schedule meetings.",
    category: "featured",
    icon: calendarIcon,
    tools: ["list_events", "get_event", "create_event"],
  },
  {
    id: "gmail",
    name: "Gmail",
    description: "Search emails, read threads, and draft replies.",
    category: "productivity",
    icon: gmailIcon,
    tools: ["search_email", "read_email", "draft_email"],
  },
  {
    id: "notion",
    name: "Notion",
    description: "Search workspace notes, trackers, and databases.",
    category: "productivity",
    icon: notionIcon,
    tools: ["search_pages", "get_page", "query_database"],
  },
  {
    id: "outlook",
    name: "Outlook",
    description: "Access Outlook mail and calendar schedules.",
    category: "productivity",
    icon: outlookIcon,
    tools: ["list_events", "search_mail"],
  },
  {
    id: "atlassian",
    name: "Atlassian",
    description: "Search Jira tickets and Confluence knowledge bases.",
    category: "productivity",
    icon: atlassianIcon,
    tools: ["search_jira", "get_issue", "read_confluence"],
  },
];

export function getConnector(id: string): Connector | null {
  return connectors.find((connector) => connector.id === id) ?? null;
}
