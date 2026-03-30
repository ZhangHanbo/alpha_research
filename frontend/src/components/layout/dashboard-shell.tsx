"use client";

import { ReactNode } from "react";
import { useResearchStore } from "@/hooks/use-research-store";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

interface DashboardShellProps {
  sidebar: ReactNode;
  main: ReactNode;
  topBar: ReactNode;
}

export function DashboardShell({ sidebar, main, topBar }: DashboardShellProps) {
  const { activityPanelOpen, setActivityPanelOpen } = useResearchStore();

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* Top bar */}
      <header className="flex items-center gap-2 border-b px-4 py-2.5 shrink-0">
        <button
          onClick={() => setActivityPanelOpen(!activityPanelOpen)}
          className="p-1.5 rounded-md hover:bg-muted text-muted-foreground"
          title={activityPanelOpen ? "Hide activity" : "Show activity"}
        >
          {activityPanelOpen ? (
            <PanelLeftClose className="h-4 w-4" />
          ) : (
            <PanelLeftOpen className="h-4 w-4" />
          )}
        </button>
        <div className="flex-1">{topBar}</div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {activityPanelOpen && (
          <aside className="w-80 shrink-0 border-r overflow-y-auto bg-muted/30">
            {sidebar}
          </aside>
        )}
        <main className="flex-1 overflow-y-auto p-4">{main}</main>
      </div>
    </div>
  );
}
