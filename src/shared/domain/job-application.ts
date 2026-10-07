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
  /** Model that produced the evaluation, as reported by Foundry. */
  model?: string;
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

/** How far the reviewer agent agrees with the evaluator agent. */
export type ReviewAgreement = "Agrees" | "Partially agrees" | "Disagrees";

/** One inconsistency the reviewer found in the evaluation. */
export interface ReviewFinding {
  type: "Unsupported claim" | "Missed evidence" | "Score mismatch" | "Potential bias" | "Overconfidence";
  severity: "Low" | "Medium" | "High";
  description: string;
}

/** Checker-agent review of the evaluation, embedded in an application. */
export interface ApplicationReview {
  status: EvaluationStatus;
  startedAt: string;
  completedAt?: string;
  agentName: string;
  agentVersion?: string;
  agentExecutionId?: string;
  /** Model that produced the review, as reported by Foundry. */
  model?: string;
  /** Foundry response ID of the evaluation that was reviewed. */
  reviewedEvaluationId?: string;
  originalScore?: number;
  validatedScore?: number;
  finalRecommendation?: EvaluationRecommendation;
  agreement?: ReviewAgreement;
  confidence?: "High" | "Medium" | "Low";
  summary?: string;
  comments: string[];
  inconsistencies: ReviewFinding[];
  errorMessage?: string;
}

/** Recruiter's rating of the AI assessment, used as feedback for the agents. */
export type AiAssessmentRating = "Accurate" | "Partially accurate" | "Inaccurate";

/** Recruiter approval: the final decision plus a snapshot of the AI advice it was based on. */
export interface ApplicationDecision {
  status: "Advanced" | "Rejected";
  comment: string;
  decidedBy: string;
  decidedAt: string;
  aiRating?: AiAssessmentRating | null;
  /** Free-text feedback for improving the agents. */
  agentFeedback?: string;
  aiRecommendation?: EvaluationRecommendation | null;
  aiScore?: number | null;
  /** Whether the decision matched a clear-cut AI recommendation; null when the AI did not commit. */
  followedAi?: boolean | null;
  evaluationExecutionId?: string | null;
  reviewExecutionId?: string | null;
}

/** Recruiter feedback on the AI workflow for one decision, without candidate personal data. */
export interface AgentFeedback {
  applicationId: string;
  jobId: string;
  decidedAt: string;
  decision: "Advanced" | "Rejected";
  aiRecommendation?: EvaluationRecommendation | null;
  followedAi?: boolean | null;
  aiRating?: AiAssessmentRating | null;
  agentFeedback: string;
  evaluationScore?: number | null;
  validatedScore?: number | null;
  reviewerAgreement?: ReviewAgreement | null;
  evaluatorVersion?: string | null;
  reviewerVersion?: string | null;
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
  /** AI evaluation (maker); absent until the evaluator has started. */
  evaluation?: ApplicationEvaluation | null;
  /** AI review of the evaluation (checker); absent until the reviewer has started. */
  review?: ApplicationReview | null;
  /** Recruiter decision, when made. */
  decision?: ApplicationDecision | null;
}
