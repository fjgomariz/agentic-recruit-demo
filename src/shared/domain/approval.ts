/** Human decision state of an approval workflow. */
export type ApprovalStatus = "Pending" | "Approved" | "Rejected" | "Changes Requested";

/** Type of business object protected by human approval. */
export type ApprovalTargetType = "Job" | "CandidateApplication";

/** Human approval gate for a versioned job or candidate application decision. */
export interface ApprovalWorkflow {
  /** Stable approval workflow identifier. */
  id: string;
  /** Kind of entity awaiting a decision. */
  targetType: ApprovalTargetType;
  /** Identifier of the job or application awaiting approval. */
  targetId: string;
  /** Current human approval state. */
  status: ApprovalStatus;
  /** Display name of the person who requested approval. */
  requestedBy: string;
  /** ISO 8601 timestamp at which approval was requested. */
  requestedAt: string;
  /** Display name of the accountable reviewer, when assigned. */
  reviewedBy?: string;
  /** ISO 8601 decision timestamp, when reviewed. */
  reviewedAt?: string;
  /** Optional reviewer rationale or requested changes. */
  comment?: string;
  /** Agent execution whose output is being reviewed, when applicable. */
  agentExecutionId?: string;
}
