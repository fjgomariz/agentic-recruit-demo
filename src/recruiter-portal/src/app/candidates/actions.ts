"use server";

import { revalidatePath } from "next/cache";
import type { AiAssessmentRating } from "@domain";
import { ApiError, clearApplicationDecision, decideApplication, evaluateApplication, reviewApplication } from "@/data/jobs";
import { currentUser } from "@/lib/user";

const ratings: AiAssessmentRating[] = ["Accurate", "Partially accurate", "Inaccurate"];

export interface CandidateActionState {
  error?: string;
}

function failure(error: unknown, fallback: string): CandidateActionState {
  return { error: error instanceof ApiError ? error.message : fallback };
}

function refresh(id: string) {
  revalidatePath("/", "layout");
  revalidatePath(`/candidates/${id}`);
}

/** Starts the full AI assessment (evaluator, then reviewer); the page polls until it completes. */
export async function startEvaluation(id: string): Promise<CandidateActionState> {
  try {
    await evaluateApplication(id);
  } catch (error) {
    return failure(error, "The evaluation could not be started. Try again.");
  }
  refresh(id);
  return {};
}

/** Re-runs only the reviewer agent on the current evaluation. */
export async function startReview(id: string): Promise<CandidateActionState> {
  try {
    await reviewApplication(id);
  } catch (error) {
    return failure(error, "The review could not be started. Try again.");
  }
  refresh(id);
  return {};
}

/** Human approval: records Advance or Reject, the recruiter's rating of the AI assessment, and feedback for the agents. */
export async function recordDecision(id: string, requiresRating: boolean, _: CandidateActionState, formData: FormData): Promise<CandidateActionState> {
  const status = formData.get("decision");
  if (status !== "Advanced" && status !== "Rejected") return { error: "Choose Advance or Reject." };
  const rating = formData.get("aiRating");
  const aiRating = ratings.find((value) => value === rating);
  if (requiresRating && !aiRating) return { error: "Rate the AI assessment before deciding. Your rating helps improve the agents." };
  try {
    await decideApplication(id, {
      status,
      comment: String(formData.get("comment") ?? "").trim(),
      decidedBy: (await currentUser()).name,
      aiRating: aiRating ?? null,
      agentFeedback: String(formData.get("agentFeedback") ?? "").trim(),
    });
  } catch (error) {
    return failure(error, "The decision could not be saved. Try again.");
  }
  refresh(id);
  return {};
}

/** Clears the decision so the recruiter can decide again. */
export async function reopenDecision(id: string): Promise<CandidateActionState> {
  try {
    await clearApplicationDecision(id);
  } catch (error) {
    return failure(error, "The decision could not be changed. Try again.");
  }
  refresh(id);
  return {};
}
