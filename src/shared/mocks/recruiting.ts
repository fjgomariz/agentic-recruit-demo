import type { Candidate, CandidateApplication, CandidateEvaluation, EvaluationReport, Resume } from "../domain";
import { createMockCandidate, createMockCandidateApplication, createMockCandidateEvaluation, createMockEvaluationReport, createMockEvaluationScore, createMockResume } from "./factories";

/** Canonical mock candidates. */
export const mockCandidates: Candidate[] = [
  createMockCandidate({ id: "olivia-bennett", firstName: "Olivia", lastName: "Bennett", email: "olivia.bennett@example.demo", location: "London, UK", profileUrl: "https://example.demo/olivia-bennett" }),
  createMockCandidate({ id: "marcus-chen", firstName: "Marcus", lastName: "Chen", email: "marcus.chen@example.demo", location: "Manchester, UK" }),
  createMockCandidate({ id: "sofia-martin", firstName: "Sofia", lastName: "Martin", email: "sofia.martin@example.demo", location: "Paris, FR" }),
  createMockCandidate({ id: "james-wilson", firstName: "James", lastName: "Wilson", email: "james.wilson@example.demo", location: "Brooklyn, US" }),
];

const resumeSummaries = [
  "Senior product designer with eight years of experience shaping B2B SaaS products, including analytics and workflow tools.",
  "Product designer focused on accessible consumer and B2B platforms, with recent experience leading a design system migration.",
  "Visual designer transitioning into product design after leading brand and web experiences for a growth-stage company.",
  "Customer success leader with seven years supporting enterprise software accounts and renewal programs.",
];

/** Canonical mock resume metadata. */
export const mockResumes: Resume[] = mockCandidates.map((candidate, index) => createMockResume({ id: `resume-${candidate.id}`, candidateId: candidate.id, fileName: `${candidate.firstName.toLowerCase()}-${candidate.lastName.toLowerCase()}-resume.pdf`, storageReference: `mock://resumes/${candidate.id}.pdf`, summary: resumeSummaries[index], uploadedAt: `2026-09-0${index < 3 ? 2 - Math.min(index, 1) : 2}T08:55:00Z` }));

const applications = [
  { candidateId: "olivia-bennett", jobId: "senior-product-designer", appliedAt: "2026-09-02T09:00:00Z", stage: "Recruiter review" as const, status: "In review" as const },
  { candidateId: "marcus-chen", jobId: "senior-product-designer", appliedAt: "2026-09-01T09:00:00Z", stage: "Recruiter review" as const, status: "In review" as const },
  { candidateId: "sofia-martin", jobId: "senior-product-designer", appliedAt: "2026-08-31T09:00:00Z", stage: "AI review" as const, status: "In review" as const },
  { candidateId: "james-wilson", jobId: "customer-success-manager", appliedAt: "2026-09-02T10:00:00Z", stage: "Hiring manager review" as const, status: "Advanced" as const },
];

/** Canonical mock applications linking candidates, jobs, resumes, and evaluations. */
export const mockCandidateApplications: CandidateApplication[] = applications.map((application) => createMockCandidateApplication({ id: `application-${application.candidateId}`, candidateId: application.candidateId, jobId: application.jobId, resumeId: `resume-${application.candidateId}`, evaluationId: `evaluation-${application.candidateId}`, appliedAt: application.appliedAt, stage: application.stage, status: application.status }));

const reportContent = [
  { score: 92, strengths: ["Relevant enterprise product experience", "Strong portfolio evidence for systems design", "Clear cross-functional leadership examples"], considerations: ["Limited evidence of recruiting domain experience"], recommendation: "Strongly recommend progressing to a recruiter conversation." },
  { score: 86, strengths: ["Accessible design practice", "Design system leadership", "Well-structured case studies"], considerations: ["Enterprise workflow experience needs validation"], recommendation: "Recommend progressing, with focus on domain depth during screening." },
  { score: 74, strengths: ["Strong visual craft", "Experience in fast-moving teams"], considerations: ["Limited evidence against senior product criteria", "Portfolio context is incomplete"], recommendation: "Recruiter review needed before making a progression decision." },
  { score: 89, strengths: ["Executive account management", "Retention and expansion record", "Relevant enterprise software background"], considerations: ["Needs confirmation of travel availability"], recommendation: "Recommend progressing to hiring manager review." },
];

/** Canonical mock evaluation reports. */
export const mockEvaluationReports: EvaluationReport[] = mockCandidates.map((candidate, index) => {
  const content = reportContent[index];
  return createMockEvaluationReport({ id: `report-${candidate.id}`, evaluationId: `evaluation-${candidate.id}`, overallScore: content.score, summary: resumeSummaries[index], strengths: content.strengths, considerations: content.considerations, recommendation: content.recommendation, scores: [createMockEvaluationScore({ id: `score-${candidate.id}-experience`, value: content.score, rationale: content.recommendation })], generatedAt: "2026-09-02T09:01:00Z" });
});

/** Canonical mock candidate evaluations. */
export const mockCandidateEvaluations: CandidateEvaluation[] = mockCandidates.map((candidate, index) => createMockCandidateEvaluation({ id: `evaluation-${candidate.id}`, applicationId: `application-${candidate.id}`, status: index === 2 ? "Needs review" : "Completed", agentExecutionId: index === 2 ? "run_84f21" : "run_84f2a", reportId: `report-${candidate.id}`, startedAt: "2026-09-02T09:00:10Z", completedAt: index === 2 ? undefined : "2026-09-02T09:00:24Z" }));

/** Resolves the canonical entities required by a recruiter candidate view. */
export function getCandidateApplicationDetails(candidateId: string) {
  const candidate = mockCandidates.find((item) => item.id === candidateId);
  if (!candidate) return undefined;
  const application = mockCandidateApplications.find((item) => item.candidateId === candidate.id);
  const resume = application ? mockResumes.find((item) => item.id === application.resumeId) : undefined;
  const evaluation = application ? mockCandidateEvaluations.find((item) => item.id === application.evaluationId) : undefined;
  const report = evaluation ? mockEvaluationReports.find((item) => item.id === evaluation.reportId) : undefined;
  return application && resume && evaluation && report ? { candidate, application, resume, evaluation, report } : undefined;
}

/** Complete candidate views composed from canonical mock entities. */
export const mockCandidateApplicationDetails = mockCandidates.flatMap((candidate) => {
  const details = getCandidateApplicationDetails(candidate.id);
  return details ? [details] : [];
});
