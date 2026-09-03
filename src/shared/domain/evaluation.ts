import type { CandidateApplication } from "./candidate";

/** Lifecycle state of a candidate evaluation. */
export type EvaluationStatus = "Completed" | "In progress" | "Needs review" | "Failed";

/** One normalized scoring dimension in an evaluation report. */
export interface EvaluationScore {
  /** Stable score identifier. */
  id: string;
  /** Human-readable scoring criterion. */
  criterion: string;
  /** Numeric score achieved. */
  value: number;
  /** Maximum possible score. */
  maximumValue: number;
  /** Evidence-based explanation for the score. */
  rationale?: string;
}

/** Recruiter-readable report produced from a candidate evaluation. */
export interface EvaluationReport {
  /** Stable report identifier. */
  id: string;
  /** Evaluation that owns this report. */
  evaluationId: string;
  /** Overall normalized score from 0 through 100. */
  overallScore: number;
  /** Concise outcome summary. */
  summary: string;
  /** Evidence-backed candidate strengths. */
  strengths: string[];
  /** Gaps, unknowns, or areas requiring human validation. */
  considerations: string[];
  /** Advisory recommendation for recruiter review. */
  recommendation: string;
  /** Individual scoring dimensions. */
  scores: EvaluationScore[];
  /** ISO 8601 report creation timestamp. */
  generatedAt: string;
}

/** Evaluation of one application against the criteria of its related job. */
export interface CandidateEvaluation {
  /** Stable evaluation identifier. */
  id: string;
  /** Application being evaluated; this links the candidate, resume, and job. */
  applicationId: CandidateApplication["id"];
  /** Current evaluation lifecycle state. */
  status: EvaluationStatus;
  /** Agent execution that performed the evaluation. */
  agentExecutionId: string;
  /** Generated report, when evaluation output is available. */
  reportId?: EvaluationReport["id"];
  /** ISO 8601 evaluation start timestamp. */
  startedAt: string;
  /** ISO 8601 completion timestamp, when complete. */
  completedAt?: string;
}
