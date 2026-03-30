import type { Paper, Evaluation, GraphNode, GraphEdge } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Papers
export async function getPapers(params?: {
  topic?: string;
  limit?: number;
}): Promise<Paper[]> {
  const sp = new URLSearchParams();
  if (params?.topic) sp.set("topic", params.topic);
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiFetch(`/api/papers${qs ? `?${qs}` : ""}`);
}

export async function getPaper(id: string): Promise<Paper> {
  return apiFetch(`/api/papers/${encodeURIComponent(id)}`);
}

export async function getPaperEvaluations(
  paperId: string
): Promise<Evaluation[]> {
  return apiFetch(
    `/api/papers/${encodeURIComponent(paperId)}/evaluations`
  );
}

// Evaluations
export async function getEvaluations(params?: {
  cycle_id?: string;
  mode?: string;
}): Promise<Evaluation[]> {
  const sp = new URLSearchParams();
  if (params?.cycle_id) sp.set("cycle_id", params.cycle_id);
  if (params?.mode) sp.set("mode", params.mode);
  const qs = sp.toString();
  return apiFetch(`/api/evaluations${qs ? `?${qs}` : ""}`);
}

export async function submitFeedback(
  evalId: string,
  feedback: { source: string; content: string }
): Promise<{ id: number }> {
  return apiFetch(`/api/evaluations/${evalId}/feedback`, {
    method: "POST",
    body: JSON.stringify(feedback),
  });
}

// Graph
export async function getGraphNodes(): Promise<GraphNode[]> {
  return apiFetch("/api/graph/nodes");
}

export async function getGraphEdges(): Promise<GraphEdge[]> {
  return apiFetch("/api/graph/edges");
}

// Agent
export async function startRun(params: {
  mode: string;
  question: string;
  venue?: string;
}): Promise<{ run_id: string }> {
  return apiFetch("/api/agent/run", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getAgentStatus(): Promise<{
  status: string;
  iteration?: number;
}> {
  return apiFetch("/api/agent/status");
}

export function getStreamUrl(): string {
  return `${API_BASE}/api/agent/stream`;
}
