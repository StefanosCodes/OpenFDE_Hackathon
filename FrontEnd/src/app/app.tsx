import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/app/layouts/app-shell";
import { AgentProvider } from "@/app/providers/agent-provider";
import { ThemeProvider } from "@/app/providers/theme-provider";
import { AgentCanvasPage } from "@/pages/agent-canvas/ui/agent-canvas-page";
import { AgentDesignPage } from "@/pages/agent-design/ui/agent-design-page";
import { AgentWorkspaceLayout } from "@/pages/agent-workspace/ui/agent-workspace-layout";
import { WorkspaceEmptyPage } from "@/pages/agent-workspace/ui/workspace-empty-page";
import { AgentsPage } from "@/pages/agents/ui/agents-page";
import { ConnectorsPage } from "@/pages/connectors/ui/connectors-page";

export function App() {
  return (
    <ThemeProvider>
      <AgentProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/agents" replace />} />
              <Route path="agents" element={<AgentsPage />} />
              <Route path="agents/new" element={<AgentDesignPage />} />
              <Route
                path="agents/:agentId/design"
                element={<AgentDesignPage />}
              />
              <Route path="connectors" element={<ConnectorsPage />} />
            </Route>
            <Route element={<AgentWorkspaceLayout />}>
              <Route
                path="agents/:agentId/canvas"
                element={<AgentCanvasPage />}
              />
              <Route
                path="agents/:agentId/knowledge"
                element={<WorkspaceEmptyPage kind="knowledge" />}
              />
              <Route
                path="agents/:agentId/intents"
                element={<WorkspaceEmptyPage kind="intents" />}
              />
              <Route
                path="agents/:agentId/datasets"
                element={<WorkspaceEmptyPage kind="datasets" />}
              />
            </Route>
            <Route path="*" element={<Navigate to="/agents" replace />} />
          </Routes>
        </BrowserRouter>
      </AgentProvider>
    </ThemeProvider>
  );
}
