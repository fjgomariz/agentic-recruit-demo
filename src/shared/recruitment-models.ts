export type JobStatus = "Draft" | "Pending Approval" | "Published" | "Closed";
export type EvaluationStatus = "Completed" | "In progress" | "Needs review";

export interface Job {
  id: string;
  title: string;
  department: string;
  location: string;
  status: JobStatus;
  applicants: number;
  createdAt: string;
  hiringManager: string;
  aiDescription: string;
  requirements: string[];
}

export interface Candidate {
  id: string;
  name: string;
  initials: string;
  roleId: string;
  location: string;
  email: string;
  appliedAt: string;
  score: number;
  evaluationStatus: EvaluationStatus;
  stage: string;
  resumeSummary: string;
  strengths: string[];
  considerations: string[];
  recommendation: string;
}

export interface AgentRun {
  id: string;
  agent: string;
  model: string;
  status: "Completed" | "Running" | "Needs review";
  duration: string;
  cost: string;
  startedAt: string;
}
