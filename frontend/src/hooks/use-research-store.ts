import { create } from "zustand";
import type {
  AgentEvent,
  AgentStep,
  AgentStatus,
  Evaluation,
  GraphNode,
  GraphEdge,
  ResearchMode,
  Venue,
} from "@/lib/types";

interface ResearchState {
  // Agent
  agentStatus: AgentStatus;
  currentRunId: string | null;
  steps: AgentStep[];

  // Data
  evaluations: Evaluation[];
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];

  // UI
  activeView: "table" | "graph";
  selectedPaperId: string | null;
  activityPanelOpen: boolean;

  // Config
  currentQuestion: string;
  currentMode: ResearchMode;
  currentVenue: Venue;

  // Actions
  setAgentStatus: (s: AgentStatus) => void;
  setCurrentRunId: (id: string | null) => void;
  addStep: (step: AgentStep) => void;
  updateStep: (id: string, u: Partial<AgentStep>) => void;
  addEventToStep: (stepId: string, e: AgentEvent) => void;
  clearSteps: () => void;
  setEvaluations: (evals: Evaluation[]) => void;
  setGraphData: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  setActiveView: (v: "table" | "graph") => void;
  setSelectedPaperId: (id: string | null) => void;
  setActivityPanelOpen: (open: boolean) => void;
  setCurrentQuestion: (q: string) => void;
  setCurrentMode: (m: ResearchMode) => void;
  setCurrentVenue: (v: Venue) => void;
}

export const useResearchStore = create<ResearchState>((set) => ({
  agentStatus: "idle",
  currentRunId: null,
  steps: [],
  evaluations: [],
  graphNodes: [],
  graphEdges: [],
  activeView: "table",
  selectedPaperId: null,
  activityPanelOpen: true,
  currentQuestion: "",
  currentMode: "digest",
  currentVenue: "RSS",

  setAgentStatus: (s) => set({ agentStatus: s }),
  setCurrentRunId: (id) => set({ currentRunId: id }),
  addStep: (step) => set((st) => ({ steps: [...st.steps, step] })),
  updateStep: (id, u) =>
    set((st) => ({
      steps: st.steps.map((s) => (s.id === id ? { ...s, ...u } : s)),
    })),
  addEventToStep: (stepId, e) =>
    set((st) => ({
      steps: st.steps.map((s) =>
        s.id === stepId ? { ...s, events: [...s.events, e] } : s
      ),
    })),
  clearSteps: () => set({ steps: [] }),
  setEvaluations: (evals) => set({ evaluations: evals }),
  setGraphData: (nodes, edges) => set({
    graphNodes: nodes,
    graphEdges: edges,
  }),
  setActiveView: (v) => set({ activeView: v }),
  setSelectedPaperId: (id) => set({ selectedPaperId: id }),
  setActivityPanelOpen: (open) => set({ activityPanelOpen: open }),
  setCurrentQuestion: (q) => set({ currentQuestion: q }),
  setCurrentMode: (m) => set({ currentMode: m }),
  setCurrentVenue: (v) => set({ currentVenue: v }),
}));
