'use client';

import { useCallback, useState } from 'react';
import { DashboardShell } from '@/components/layout/dashboard-shell';
import { ActivityTimeline } from '@/components/activity/activity-timeline';
import { EvaluationTable } from '@/components/evaluation/evaluation-table';
import { KnowledgeGraph } from '@/components/graph/knowledge-graph';
import { ProjectList } from '@/components/project/project-list';
import { ProjectOverview } from '@/components/project/project-overview';
import { CreateProjectDialog } from '@/components/project/create-project-dialog';
import { useResearchStore } from '@/hooks/use-research-store';
import { useEvaluations } from '@/hooks/use-evaluations';
import { useKnowledgeGraph } from '@/hooks/use-knowledge-graph';
import { useEventStream } from '@/hooks/use-event-stream';
import { startRun } from '@/lib/api';
import type { Venue, ResearchMode } from '@/lib/types';

const VENUES: Venue[] = ['IJRR', 'T-RO', 'RSS', 'CoRL', 'RA-L', 'ICRA', 'IROS'];
const MODES: ResearchMode[] = ['digest', 'deep', 'survey'];

type MainView = 'projects' | 'overview' | 'research';

export default function Home() {
  const {
    activeView,
    setActiveView,
    currentQuestion,
    setCurrentQuestion,
    currentMode,
    setCurrentMode,
    currentVenue,
    setCurrentVenue,
    agentStatus,
    setAgentStatus,
    setCurrentRunId,
    clearSteps,
  } = useResearchStore();

  const { evaluations } = useEvaluations();
  const { nodes, edges } = useKnowledgeGraph();
  const { connect, disconnect } = useEventStream();

  const [mainView, setMainView] = useState<MainView>('projects');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const handleSelectProject = useCallback((projectId: string) => {
    setSelectedProjectId(projectId);
    setMainView('research');
  }, []);

  const handleRun = useCallback(async () => {
    if (!currentQuestion.trim() || agentStatus === 'running') return;
    try {
      clearSteps();
      setAgentStatus('running');
      const { run_id } = await startRun({
        mode: currentMode,
        question: currentQuestion,
        venue: currentVenue,
      });
      setCurrentRunId(run_id);
      connect();
    } catch {
      setAgentStatus('error');
    }
  }, [
    currentQuestion,
    currentMode,
    currentVenue,
    agentStatus,
    clearSteps,
    setAgentStatus,
    setCurrentRunId,
    connect,
  ]);

  const handleStop = useCallback(() => {
    disconnect();
    setAgentStatus('idle');
  }, [disconnect, setAgentStatus]);

  const renderMainContent = () => {
    if (mainView === 'projects') {
      return (
        <ProjectList
          onSelect={handleSelectProject}
          onCreateClick={() => setShowCreateDialog(true)}
        />
      );
    }
    if (mainView === 'overview' && selectedProjectId) {
      return <ProjectOverview projectId={selectedProjectId} />;
    }
    // research view
    return activeView === 'table' ? (
      <EvaluationTable evaluations={evaluations} />
    ) : (
      <KnowledgeGraph nodes={nodes} edges={edges} />
    );
  };

  return (
    <>
      <DashboardShell
        topBar={
          <div className="flex items-center gap-3">
            <h1 className="text-base font-semibold whitespace-nowrap">
              Alpha Research
            </h1>

            {/* Projects button */}
            <button
              onClick={() => { setMainView('projects'); }}
              className={`rounded-md px-3 py-1.5 text-sm font-medium border border-input ${
                mainView === 'projects'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-foreground hover:bg-muted'
              }`}
            >
              Projects
            </button>

            {/* Project selector */}
            {selectedProjectId && mainView !== 'projects' && (
              <button
                onClick={() => setMainView('overview')}
                className={`rounded-md px-3 py-1.5 text-sm font-medium border border-input ${
                  mainView === 'overview'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-background text-foreground hover:bg-muted'
                }`}
              >
                Overview
              </button>
            )}

            {selectedProjectId && (
              <>
                <input
                  type="text"
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleRun()}
                  placeholder="Research question..."
                  className="flex-1 min-w-0 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                  disabled={agentStatus === 'running'}
                />

                <select
                  value={currentMode}
                  onChange={(e) => setCurrentMode(e.target.value as ResearchMode)}
                  className="rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                >
                  {MODES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>

                <select
                  value={currentVenue}
                  onChange={(e) => setCurrentVenue(e.target.value as Venue)}
                  className="rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                >
                  {VENUES.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>

                {agentStatus === 'running' ? (
                  <button
                    onClick={handleStop}
                    className="inline-flex items-center gap-1.5 rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground hover:bg-destructive/90"
                  >
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={handleRun}
                    disabled={!currentQuestion.trim()}
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  >
                    Run
                  </button>
                )}

                <div className="flex rounded-md border border-input overflow-hidden">
                  <button
                    onClick={() => { setActiveView('table'); setMainView('research'); }}
                    className={`px-3 py-1.5 text-sm font-medium ${
                      activeView === 'table' && mainView === 'research'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-background text-foreground hover:bg-muted'
                    }`}
                  >
                    Table
                  </button>
                  <button
                    onClick={() => { setActiveView('graph'); setMainView('research'); }}
                    className={`px-3 py-1.5 text-sm font-medium border-l border-input ${
                      activeView === 'graph' && mainView === 'research'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-background text-foreground hover:bg-muted'
                    }`}
                  >
                    Graph
                  </button>
                </div>
              </>
            )}
          </div>
        }
        sidebar={<ActivityTimeline />}
        main={renderMainContent()}
      />

      {showCreateDialog && (
        <CreateProjectDialog
          onCreated={(manifest) => {
            setShowCreateDialog(false);
            setSelectedProjectId(manifest.project_id);
            setMainView('research');
          }}
          onCancel={() => setShowCreateDialog(false)}
        />
      )}
    </>
  );
}
