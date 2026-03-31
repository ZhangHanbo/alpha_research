'use client';

import { useEffect, useState, useCallback } from 'react';
import { getProject, getProjectSnapshots, getProjectRuns, resumeProject, createManualSnapshot } from '@/lib/api';
import type { ProjectManifest, ProjectState, ProjectSnapshot, ProjectRun } from '@/lib/types';

const TYPE_COLORS: Record<string, string> = {
  literature: 'bg-blue-100 text-blue-800',
  codebase: 'bg-green-100 text-green-800',
  hybrid: 'bg-purple-100 text-purple-800',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  active: 'bg-emerald-100 text-emerald-800',
  paused: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-blue-100 text-blue-800',
  archived: 'bg-red-100 text-red-800',
};

const RUN_STATUS_COLORS: Record<string, string> = {
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-emerald-100 text-emerald-800',
  failed: 'bg-red-100 text-red-800',
};

interface ProjectOverviewProps {
  projectId: string;
}

export function ProjectOverview({ projectId }: ProjectOverviewProps) {
  const [manifest, setManifest] = useState<ProjectManifest | null>(null);
  const [state, setState] = useState<ProjectState | null>(null);
  const [snapshots, setSnapshots] = useState<ProjectSnapshot[]>([]);
  const [runs, setRuns] = useState<ProjectRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      getProject(projectId),
      getProjectSnapshots(projectId),
      getProjectRuns(projectId),
    ])
      .then(([proj, snaps, runList]) => {
        setManifest(proj.manifest);
        setState(proj.state);
        setSnapshots(snaps);
        setRuns(runList);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function handleResume() {
    setActionLoading('resume');
    try {
      const newState = await resumeProject(projectId);
      setState(newState);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Resume failed');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleSnapshot() {
    setActionLoading('snapshot');
    try {
      const snap = await createManualSnapshot(projectId);
      setSnapshots((prev) => [snap, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Snapshot failed');
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) return <div className="flex items-center justify-center py-20 text-muted-foreground">Loading...</div>;
  if (error) return <div className="flex items-center justify-center py-20 text-destructive">Error: {error}</div>;
  if (!manifest || !state) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-semibold">{manifest.name}</h2>
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${TYPE_COLORS[manifest.project_type] || ''}`}>
              {manifest.project_type}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${STATUS_COLORS[manifest.status] || ''}`}>
              {manifest.status}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{manifest.primary_question}</p>
          {manifest.description && <p className="text-sm text-muted-foreground mt-1">{manifest.description}</p>}
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={handleResume} disabled={actionLoading !== null}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
            {actionLoading === 'resume' ? 'Resuming...' : 'Resume'}
          </button>
          <button onClick={handleSnapshot} disabled={actionLoading !== null}
            className="rounded-md border border-input px-3 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-50">
            {actionLoading === 'snapshot' ? 'Saving...' : 'Snapshot'}
          </button>
        </div>
      </div>

      {/* State */}
      <div className="rounded-lg border p-4 space-y-2">
        <h3 className="text-sm font-semibold">Project State</h3>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div><span className="text-muted-foreground">Status:</span> {state.current_status}</div>
          <div><span className="text-muted-foreground">Resume required:</span> {state.resume_required ? 'Yes' : 'No'}</div>
          <div><span className="text-muted-foreground">Source changed:</span> {state.source_changed_since_last_snapshot ? 'Yes' : 'No'}</div>
          <div><span className="text-muted-foreground">Last resumed:</span> {state.last_resumed_at ? new Date(state.last_resumed_at).toLocaleString() : 'Never'}</div>
        </div>
      </div>

      {/* Snapshots */}
      <div>
        <h3 className="text-sm font-semibold mb-3">Snapshots</h3>
        {snapshots.length === 0 ? (
          <p className="text-sm text-muted-foreground">No snapshots yet.</p>
        ) : (
          <div className="space-y-2">
            {snapshots.map((snap) => (
              <div key={snap.snapshot_id} className="flex items-start gap-3 rounded-lg border p-3">
                <div className="mt-1 h-2 w-2 rounded-full bg-primary shrink-0" />
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="bg-gray-100 text-gray-700 text-xs px-1.5 py-0.5 rounded-full">{snap.snapshot_kind}</span>
                    <span className="text-muted-foreground text-xs">{new Date(snap.created_at).toLocaleString()}</span>
                  </div>
                  {snap.summary && <p className="text-sm mt-1">{snap.summary}</p>}
                  {snap.note && <p className="text-xs text-muted-foreground mt-0.5">{snap.note}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Runs */}
      <div>
        <h3 className="text-sm font-semibold mb-3">Run History</h3>
        {runs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No runs yet.</p>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <div key={run.run_id} className="rounded-lg border p-3">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium">{run.run_type}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${RUN_STATUS_COLORS[run.status] || 'bg-gray-100 text-gray-700'}`}>
                    {run.status}
                  </span>
                  <span className="text-xs text-muted-foreground">{new Date(run.started_at).toLocaleString()}</span>
                </div>
                {run.summary && <p className="text-sm text-muted-foreground mt-1">{run.summary}</p>}
                {run.error && <p className="text-sm text-destructive mt-1">{run.error}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
