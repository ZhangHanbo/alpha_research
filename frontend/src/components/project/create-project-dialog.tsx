'use client';

import { useState } from 'react';
import { createProject } from '@/lib/api';
import type { ProjectManifest } from '@/lib/types';

interface CreateProjectDialogProps {
  onCreated: (manifest: ProjectManifest) => void;
  onCancel: () => void;
}

export function CreateProjectDialog({ onCreated, onCancel }: CreateProjectDialogProps) {
  const [name, setName] = useState('');
  const [projectType, setProjectType] = useState<string>('literature');
  const [question, setQuestion] = useState('');
  const [description, setDescription] = useState('');
  const [sourcePath, setSourcePath] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = name.trim() !== '' && question.trim() !== '' && !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const manifest = await createProject({
        name: name.trim(),
        project_type: projectType,
        primary_question: question.trim(),
        description: description.trim() || undefined,
        source_path: sourcePath.trim() || undefined,
      });
      onCreated(manifest);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div className="bg-background border rounded-lg shadow-lg w-full max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-4">Create Project</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              placeholder="Project name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <select
              value={projectType} onChange={(e) => setProjectType(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
            >
              <option value="literature">Literature</option>
              <option value="codebase">Codebase</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Primary Question *</label>
            <input
              type="text" value={question} onChange={(e) => setQuestion(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              placeholder="What are you investigating?"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm resize-none"
              placeholder="Optional description..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Source Path</label>
            <input
              type="text" value={sourcePath} onChange={(e) => setSourcePath(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              placeholder="/path/to/source (optional)"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onCancel}
              className="rounded-md border border-input px-3 py-1.5 text-sm font-medium hover:bg-muted"
            >
              Cancel
            </button>
            <button type="submit" disabled={!canSubmit}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
