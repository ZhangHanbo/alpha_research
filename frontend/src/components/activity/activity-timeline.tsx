'use client';

import { useEffect, useRef, useState } from 'react';
import { useResearchStore } from '@/hooks/use-research-store';
import type { AgentStep, AgentEvent } from '@/lib/types';

function formatElapsed(step: AgentStep): string {
  const start = step.startTime;
  if (!start) return '';
  const end = step.endTime ?? Date.now();
  const seconds = Math.floor((end - start) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

function StatusIcon({ status }: { status: AgentStep['status'] }) {
  if (status === 'completed') {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500/20 text-green-400 text-xs font-bold">
        ✓
      </span>
    );
  }
  if (status === 'running') {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500/20 text-blue-400 text-xs animate-pulse">
        ▶
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500/20 text-red-400 text-xs font-bold">
        ✕
      </span>
    );
  }
  return (
    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-neutral-700 text-neutral-500 text-xs">
      ○
    </span>
  );
}

function eventLabel(event: AgentEvent): string {
  switch (event.type) {
    case 'tool_call':
      return `Tool: ${(event.data.name as string) ?? 'unknown'}`;
    case 'tool_result':
      return `Result: ${(event.data.summary as string) ?? 'done'}`;
    case 'activity':
      return (event.data.message as string) ?? 'Activity';
    case 'error':
      return (event.data.message as string) ?? 'Error';
    case 'step_started':
      return 'Started';
    case 'step_finished':
      return 'Finished';
    case 'run_finished':
      return 'Run complete';
    default:
      return event.type;
  }
}

function StepItem({ step }: { step: AgentStep }) {
  const [expanded, setExpanded] = useState(step.status === 'running');
  const itemRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (step.status === 'running') {
      setExpanded(true);
      itemRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [step.status]);

  const hasEvents = step.events.length > 0;

  return (
    <div ref={itemRef} className="relative pl-7">
      {/* Vertical connector line */}
      <div className="absolute left-2.5 top-0 bottom-0 w-px bg-neutral-700" />

      {/* Step header */}
      <div className="absolute left-0 top-1">
        <StatusIcon status={step.status} />
      </div>

      <button
        type="button"
        onClick={() => hasEvents && setExpanded(!expanded)}
        className="flex w-full items-center justify-between gap-2 py-1.5 text-left text-sm hover:bg-neutral-800/50 rounded px-1 -ml-1 transition-colors"
      >
        <span className="font-medium text-neutral-200 truncate">
          {hasEvents && (
            <span className="mr-1 text-neutral-500 text-xs inline-block transition-transform" style={{ transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>
              ▸
            </span>
          )}
          {step.name}
        </span>
        <span className="text-xs text-neutral-500 whitespace-nowrap tabular-nums">
          {step.status === 'running' ? (
            <RunningTimer startTime={step.startTime} />
          ) : (
            formatElapsed(step)
          )}
        </span>
      </button>

      {/* Sub-events */}
      {expanded && hasEvents && (
        <div className="ml-2 mb-2 border-l border-neutral-700/50 pl-3 space-y-0.5">
          {step.events.map((event, i) => (
            <div
              key={i}
              className={`text-xs py-0.5 ${
                event.type === 'error'
                  ? 'text-red-400'
                  : event.type === 'tool_call'
                    ? 'text-blue-300'
                    : 'text-neutral-400'
              }`}
            >
              {eventLabel(event)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RunningTimer({ startTime }: { startTime?: number }) {
  const [, tick] = useState(0);

  useEffect(() => {
    if (!startTime) return;
    const id = setInterval(() => tick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [startTime]);

  if (!startTime) return null;
  const seconds = Math.floor((Date.now() - startTime) / 1000);
  if (seconds < 60) return <>{seconds}s</>;
  return <>{Math.floor(seconds / 60)}m {seconds % 60}s</>;
}

export function ActivityTimeline() {
  const steps = useResearchStore((s) => s.steps);
  const agentStatus = useResearchStore((s) => s.agentStatus);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (agentStatus === 'running') {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [steps.length, agentStatus]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-800">
        <h2 className="text-sm font-semibold text-neutral-200">Agent Activity</h2>
        {agentStatus === 'running' && (
          <span className="flex items-center gap-1.5 text-xs text-blue-400">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
            Running
          </span>
        )}
        {agentStatus === 'error' && (
          <span className="text-xs text-red-400">Error</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2">
        {steps.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-neutral-500 text-sm gap-1">
            <span className="text-2xl">○</span>
            <span>No activity yet</span>
          </div>
        ) : (
          <div className="space-y-1">
            {steps.map((step) => (
              <StepItem key={step.id} step={step} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
    </div>
  );
}
