import { Outlet } from "react-router-dom";

import { AppSidebar } from "@/widgets/app-sidebar/ui/app-sidebar";

export function AppShell() {
  return (
    <div className="app-shell">
      <AppSidebar />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
