import type {
  AgentExecution,
  ApprovalWorkflow,
  Candidate,
  CandidateApplication,
  CandidateEvaluation,
  EvaluationReport,
  EvaluationScore,
  Job,
  Resume,
} from "../domain";

/** Creates a complete mock job with optional field overrides. */
export function createMockJob(overrides: Partial<Job> = {}): Job {
  return {
    id: "sample-job",
    title: "Sample Role",
    department: "Product",
    location: { displayName: "Remote — US", workplaceType: "Remote", countryCode: "US" },
    status: "Draft",
    employmentType: "Full-time",
    experienceLevel: "Mid",
    summary: "Help build thoughtful products for meaningful work.",
    description: "Collaborate with a multidisciplinary team to deliver clear customer outcomes.",
    responsibilities: ["Own well-defined outcomes from discovery through delivery."],
    qualifications: ["Relevant practical experience and strong collaboration skills."],
    preferredQualifications: [],
    hiringManager: "Jordan Lee",
    createdAt: "2026-09-01T09:00:00Z",
    applicantCount: 0,
    ...overrides,
  };
}

/** Creates a complete mock candidate with optional field overrides. */
export function createMockCandidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    id: "sample-candidate",
    firstName: "Taylor",
    lastName: "Morgan",
    email: "taylor.morgan@example.demo",
    location: "London, UK",
    ...overrides,
  };
}

/** Creates a complete mock resume with optional field overrides. */
export function createMockResume(overrides: Partial<Resume> = {}): Resume {
  return {
    id: "resume-sample-candidate",
    candidateId: "sample-candidate",
    fileName: "taylor-morgan-resume.pdf",
    contentType: "application/pdf",
    storageReference: "mock://resumes/taylor-morgan-resume.pdf",
    uploadedAt: "2026-09-02T08:55:00Z",
    ...overrides,
  };
}

/** Creates a complete mock candidate application with optional field overrides. */
export function createMockCandidateApplication(overrides: Partial<CandidateApplication> = {}): CandidateApplication {
  return {
    id: "application-sample-candidate",
    candidateId: "sample-candidate",
    jobId: "sample-job",
    resumeId: "resume-sample-candidate",
    stage: "AI review",
    status: "In review",
    appliedAt: "2026-09-02T09:00:00Z",
    ...overrides,
  };
}

/** Creates a complete mock evaluation score with optional field overrides. */
export function createMockEvaluationScore(overrides: Partial<EvaluationScore> = {}): EvaluationScore {
  return {
    id: "score-relevant-experience",
    criterion: "Relevant experience",
    value: 85,
    maximumValue: 100,
    ...overrides,
  };
}

/** Creates a complete mock evaluation report with optional field overrides. */
export function createMockEvaluationReport(overrides: Partial<EvaluationReport> = {}): EvaluationReport {
  return {
    id: "report-sample-application",
    evaluationId: "evaluation-sample-application",
    overallScore: 85,
    summary: "The candidate demonstrates relevant experience for this role.",
    strengths: ["Relevant practical experience"],
    considerations: ["Validate role-specific depth during recruiter review"],
    recommendation: "Recommend recruiter review.",
    scores: [createMockEvaluationScore()],
    generatedAt: "2026-09-02T09:01:00Z",
    ...overrides,
  };
}

/** Creates a complete mock candidate evaluation with optional field overrides. */
export function createMockCandidateEvaluation(overrides: Partial<CandidateEvaluation> = {}): CandidateEvaluation {
  return {
    id: "evaluation-sample-application",
    applicationId: "application-sample-candidate",
    status: "Completed",
    agentExecutionId: "run-sample-evaluation",
    reportId: "report-sample-application",
    startedAt: "2026-09-02T09:00:10Z",
    completedAt: "2026-09-02T09:00:24Z",
    ...overrides,
  };
}

/** Creates a complete mock approval workflow with optional field overrides. */
export function createMockApprovalWorkflow(overrides: Partial<ApprovalWorkflow> = {}): ApprovalWorkflow {
  return {
    id: "approval-sample-job",
    targetType: "Job",
    targetId: "sample-job",
    status: "Pending",
    requestedBy: "Jordan Lee",
    requestedAt: "2026-09-02T10:00:00Z",
    ...overrides,
  };
}

/** Creates a complete mock agent execution with optional field overrides. */
export function createMockAgentExecution(overrides: Partial<AgentExecution> = {}): AgentExecution {
  return {
    id: "run-sample-evaluation",
    agentName: "Candidate evaluation",
    model: "gpt-4.1",
    status: "Completed",
    startedAt: "2026-09-02T09:00:10Z",
    completedAt: "2026-09-02T09:00:24Z",
    durationMs: 14_200,
    estimatedCostUsd: 0.084,
    configurationVersion: "v2.3",
    relatedEntityIds: ["application-sample-candidate"],
    ...overrides,
  };
}
