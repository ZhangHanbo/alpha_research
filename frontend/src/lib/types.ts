// Paper
export interface Paper {
  arxiv_id: string | null;
  s2_id: string | null;
  doi: string | null;
  title: string;
  authors: string[];
  venue: string | null;
  year: number | null;
  abstract: string;
  url: string | null;
}

// Rubric score
export interface RubricScore {
  score: number;
  confidence: "high" | "medium" | "low";
  evidence: string[];
  reasoning: string;
}

// Task chain
export interface TaskChain {
  task: string | null;
  problem: string | null;
  challenge: string | null;
  approach: string | null;
  one_sentence: string | null;
  chain_complete: boolean;
  chain_coherent: boolean;
}

// Significance
export interface SignificanceAssessment {
  hamming_score: number;
  hamming_reasoning: string;
  concrete_consequence: string | null;
  durability_risk: "low" | "medium" | "high";
  compounding_value: "high" | "medium" | "low";
  motivation_type: "goal_driven" | "idea_driven" | "unclear";
}

// Evaluation
export interface Evaluation {
  paper_id: string;
  cycle_id: string;
  mode: string;
  status: string;
  task_chain: TaskChain | null;
  has_formal_problem_def: boolean;
  rubric_scores: Record<string, RubricScore>;
  significance_assessment: SignificanceAssessment | null;
  human_review_flags: string[];
  extraction_limitations: string[];
  // Joined paper data (returned by API)
  title?: string;
  authors?: string[];
  venue?: string | null;
  year?: number | null;
  arxiv_id?: string | null;
}

// Graph
export interface GraphNode {
  id: string;
  title: string;
  year: number | null;
  venue: string | null;
  score: number | null;
  approach_type: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation_type:
    | "extends"
    | "contradicts"
    | "supersedes"
    | "same_task"
    | "same_method"
    | "cites";
}

// Agent streaming
export interface AgentEvent {
  type:
    | "step_started"
    | "step_finished"
    | "activity"
    | "tool_call"
    | "tool_result"
    | "run_finished"
    | "error";
  data: Record<string, unknown>;
  timestamp?: string;
}

export interface AgentStep {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  startTime?: number;
  endTime?: number;
  events: AgentEvent[];
}

export type AgentStatus = "idle" | "running" | "completed" | "error";

export type Venue =
  | "IJRR"
  | "T-RO"
  | "RSS"
  | "CoRL"
  | "RA-L"
  | "ICRA"
  | "IROS";

export type ResearchMode = "digest" | "deep" | "survey" | "gap" | "frontier" | "direction";
