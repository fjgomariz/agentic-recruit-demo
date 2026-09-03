import {
  mockAgentExecutions,
  mockApprovalWorkflows,
  mockCandidateApplicationDetails,
  mockCandidateApplications,
  mockCandidateEvaluations,
  mockCandidates,
  mockEvaluationReports,
  mockResumes,
  recruiterJobs,
} from "@mocks";

/** Recruiter-visible canonical mock jobs. */
export const jobs = recruiterJobs;
/** Canonical mock candidate identities. */
export const candidates = mockCandidates;
/** Canonical mock application records. */
export const candidateApplications = mockCandidateApplications;
/** Canonical mock resume metadata. */
export const resumes = mockResumes;
/** Canonical mock candidate evaluations. */
export const candidateEvaluations = mockCandidateEvaluations;
/** Canonical mock evaluation reports. */
export const evaluationReports = mockEvaluationReports;
/** Resolved canonical records used by candidate screens. */
export const candidateDetails = mockCandidateApplicationDetails;
/** Canonical mock agent execution records. */
export const agentExecutions = mockAgentExecutions;
/** Canonical mock human approval workflows. */
export const approvalWorkflows = mockApprovalWorkflows;
