'use client';

import { useEffect, useState } from 'react';
import { getProjects } from '@/lib/api';
import type { ProjectManifest } from '@/lib/types';

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

interface ProjectListProps {
  onSelect: (projectId: string) => void;
  onCreateClick: () => void;
}

export function ProjectList({ onSelect, onCreateClick }: ProjectListProps) {
  const [projects, setProjects] = useState<ProjectManifest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getProjects()
      .then((data) => { if (!cancelled) setProjects(data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-muted-foreground">Loading projects...</div>;
  }

  if (error) {
    return <div className="flex items-center justify-center py-20 text-destructive">Error: {error}</div>;
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">Projects</h2>
        <button
          onClick={onCreateClick}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          + Create Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          No projects yet. Create one to get started.
        </div>
      ) : (
        <div className="grid gap-3">
          {projects.map((p) => (
            <button
              key={p.project_id}
              onClick={() => onSelect(p.project_id)}
              className="text-left w-full rounded-lg border border-input bg-background p-4 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium">{p.name}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${TYPE_COLORS[p.project_type] || 'bg-gray-100 text-gray-800'}`}>
                  {p.project_type}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${STATUS_COLORS[p.status] || 'bg-gray-100 text-gray-800'}`}>
                  {p.status}
                </span>
              </div>
              <p className="text-sm text-muted-foreground line-clamp-1">{p.primary_question}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Created {new Date(p.created_at).toLocaleDateString()}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
