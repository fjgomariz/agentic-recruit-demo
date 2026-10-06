import type { JobApplication } from "@domain";

/** Single label summarizing where an application stands in the AI evaluation. */
export function evaluationLabel(application: JobApplication): string {
  const evaluation = application.evaluation;
  if (!evaluation) return "Pending evaluation";
  if (evaluation.status === "In progress") return "Evaluating…";
  if (evaluation.status === "Failed") return "Evaluation failed";
  return evaluation.recommendation ?? "Needs manual review";
}

export function isEvaluating(application: JobApplication): boolean {
  return application.evaluation?.status === "In progress";
}

export function scoreOf(application: JobApplication): number | undefined {
  const score = application.evaluation?.overallScore;
  return score === null || score === undefined ? undefined : score;
}

/** Evaluated and not yet decided: what the recruiter should look at next. */
export function awaitsDecision(application: JobApplication): boolean {
  const status = application.evaluation?.status;
  return !application.decision && (status === "Completed" || status === "Needs review");
}

/** Highest score first; unevaluated applications last, newest first among equals. */
export function byBestMatch(a: JobApplication, b: JobApplication): number {
  const difference = (scoreOf(b) ?? -1) - (scoreOf(a) ?? -1);
  return difference !== 0 ? difference : b.submittedAt.localeCompare(a.submittedAt);
}
