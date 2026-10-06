import type { EvaluationScore, EvaluationStatus } from "./evaluation";
import type { Job } from "./job";

/** Advisory outcome proposed by the candidate evaluation agent. */
export type EvaluationRecommendation = "Strong match" | "Possible match" | "Not a match" | "Needs manual review";

/** AI evaluation embedded in an application. */
export interface ApplicationEvaluation {
  status: EvaluationStatus;
  startedAt: string;
  completedAt?: string;
  agentName: string;
  agentVersion?: string;
  /** Foundry response ID, for trace correlation. */
  agentExecutionId?: string;
  /** Overall fit from 0 to 100. */
  overallScore?: number;
  recommendation?: EvaluationRecommendation;
  summary?: string;
  strengths: string[];
  considerations: string[];
  /** One entry per criterion, scored from 0 to 5. */
  scores: EvaluationScore[];
  errorMessage?: string;
}

/** Recruiter decision; the AI evaluation is advisory only. */
export interface ApplicationDecision {
  status: "Advanced" | "Rejected";
  comment: string;
  decidedBy: string;
  decidedAt: string;
}

/** Application submitted through the public portal, stored in Cosmos DB with its resume in Blob Storage. */
export interface JobApplication {
  /** Generated application identifier; also names the resume blob. */
  id: string;
  /** Job the candidate applied for. */
  jobId: Job["id"];
  /** Candidate's full name. */
  candidateName: string;
  /** Candidate contact email. */
  candidateEmail: string;
  /** Optional short message from the candidate. */
  message: string;
  /** Original name of the uploaded PDF. */
  resumeFileName: string;
  /** Resume location as `<container>/<blob>`. */
  resumeBlobPath: string;
  /** ISO 8601 submission timestamp. */
  submittedAt: string;
  /** AI evaluation; absent until the evaluator has started. */
  evaluation?: ApplicationEvaluation | null;
  /** Recruiter decision, when made. */
  decision?: ApplicationDecision | null;
}
