"use server";

import { revalidatePath } from "next/cache";
import { ApiError, clearApplicationDecision, decideApplication, evaluateApplication } from "@/data/jobs";

/** Demo recruiter identity shown in the portal header; there is no sign-in yet. */
const recruiter = "Jordan Lee";

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

/** Starts the AI evaluation; the page polls until it completes. */
export async function startEvaluation(id: string): Promise<CandidateActionState> {
  try {
    await evaluateApplication(id);
  } catch (error) {
    return failure(error, "The evaluation could not be started. Try again.");
  }
  refresh(id);
  return {};
}

/** Records Advance or Reject with an optional comment. */
export async function recordDecision(id: string, _: CandidateActionState, formData: FormData): Promise<CandidateActionState> {
  const status = formData.get("decision");
  if (status !== "Advanced" && status !== "Rejected") return { error: "Choose Advance or Reject." };
  try {
    await decideApplication(id, { status, comment: String(formData.get("comment") ?? "").trim(), decidedBy: recruiter });
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
