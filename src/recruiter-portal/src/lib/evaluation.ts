import type { ApplicationEvaluation, ApplicationReview, EvaluationRecommendation, JobApplication } from "@domain";

/** Same rule as the API: a step "In progress" for longer than this was interrupted (e.g. a restart) and can be re-run. */
const STALE_AFTER_MS = 3 * 60 * 1000;

/** The step is genuinely running (in progress and not stalled). */
export function isRunning(step: ApplicationEvaluation | ApplicationReview | null | undefined): boolean {
  return step?.status === "In progress" && Date.now() - new Date(step.startedAt).getTime() < STALE_AFTER_MS;
}

/** The step was left "In progress" by an interrupted run. */
export function isStalled(step: ApplicationEvaluation | ApplicationReview | null | undefined): boolean {
  return step?.status === "In progress" && !isRunning(step);
}

/** Steps of the assessment workflow: evaluator agent (maker) → reviewer agent (checker) → recruiter approval. */
export type WorkflowStage = "Not evaluated" | "Evaluating" | "Evaluation failed" | "Reviewing" | "Awaiting approval" | "Decided";

export function workflowStage(application: JobApplication): WorkflowStage {
  if (application.decision) return "Decided";
  const evaluation = application.evaluation;
  if (!evaluation) return "Not evaluated";
  if (isRunning(evaluation)) return "Evaluating";
  if (evaluation.status === "Failed" || isStalled(evaluation)) return "Evaluation failed";
  if (isRunning(application.review)) return "Reviewing";
  return "Awaiting approval";
}

/** An AI step is running, so pages showing this application should refresh. */
export function isEvaluating(application: JobApplication): boolean {
  return isRunning(application.evaluation) || isRunning(application.review);
}

export function isReviewed(application: JobApplication): boolean {
  return application.review?.status === "Completed";
}

/** The AI advice shown to the recruiter: the reviewer's validated result when available, otherwise the evaluator's. */
export function finalRecommendation(application: JobApplication): EvaluationRecommendation | undefined {
  if (isReviewed(application)) return application.review?.finalRecommendation ?? undefined;
  const evaluation = application.evaluation;
  return evaluation && (evaluation.status === "Completed" || evaluation.status === "Needs review") ? evaluation.recommendation ?? undefined : undefined;
}

export function scoreOf(application: JobApplication): number | undefined {
  const score = isReviewed(application) ? application.review?.validatedScore : application.evaluation?.overallScore;
  return score === null || score === undefined ? undefined : score;
}

/** Single label summarizing where an application stands in the AI workflow. */
export function evaluationLabel(application: JobApplication): string {
  const evaluation = application.evaluation;
  if (!evaluation) return "Pending evaluation";
  if (isRunning(evaluation)) return "Evaluating…";
  if (evaluation.status === "Failed" || isStalled(evaluation)) return "Evaluation failed";
  if (isRunning(application.review)) return "Reviewing…";
  return finalRecommendation(application) ?? "Needs manual review";
}

/** The AI workflow has finished and the recruiter has not decided yet. */
export function awaitsDecision(application: JobApplication): boolean {
  return workflowStage(application) === "Awaiting approval";
}

/** Highest score first; unevaluated applications last, newest first among equals. */
export function byBestMatch(a: JobApplication, b: JobApplication): number {
  const difference = (scoreOf(b) ?? -1) - (scoreOf(a) ?? -1);
  return difference !== 0 ? difference : b.submittedAt.localeCompare(a.submittedAt);
}
