"use server";

import { revalidatePath } from "next/cache";
import { notFound, redirect } from "next/navigation";
import type { Job, JobStatus } from "@domain";
import { ApiError, createJob, draftJobDescription, getJob, updateJob, type JobDescriptionDraftResult, type JobDescriptionRequest } from "@/data/jobs";
import { createJobId, readJobForm, validateJobForm, type JobFormState } from "@/lib/job-form";

/** Outcome of an AI generation request returned to the job form. */
export type GenerateDescriptionState = { result: JobDescriptionDraftResult; error?: undefined } | { result?: undefined; error: string };

/** Asks the Foundry job description agent for a draft based on role facts and recruiter notes. */
export async function generateJobDescription(request: JobDescriptionRequest): Promise<GenerateDescriptionState> {
  if (!request.title.trim()) return { error: "Add a job title before generating a description." };
  if (!request.notes.trim()) return { error: "Add a few notes about the role so the agent knows what to write." };
  try {
    return { result: await draftJobDescription({ ...request, title: request.title.trim(), notes: request.notes.trim() }) };
  } catch (error) {
    if (error instanceof ApiError) return { error: `The AI agent could not generate a description: ${error.message}` };
    return { error: "The AI agent did not respond in time. Try again." };
  }
}

/** Creates a job, or updates the job identified by the hidden `id` field, in Cosmos DB via the API. */
export async function saveJob(_: JobFormState, formData: FormData): Promise<JobFormState> {
  const values = readJobForm(formData);
  const { content, fieldErrors } = validateJobForm(values);
  if (!content) return { values, fieldErrors };

  const existingId = String(formData.get("id") ?? "");
  let saved: Job;
  try {
    if (existingId) {
      const current = await getJob(existingId);
      if (!current) return { values, error: `Job '${existingId}' no longer exists.` };
      saved = await updateJob({ ...current, ...content });
    } else {
      saved = await createJob({
        ...content,
        id: createJobId(content.title),
        status: formData.get("intent") === "draft" ? "Draft" : "Pending Approval",
        createdAt: new Date().toISOString(),
        applicantCount: 0,
      });
    }
  } catch (error) {
    return { values, error: error instanceof ApiError ? error.message : "The job could not be saved. Try again." };
  }

  revalidatePath("/", "layout");
  redirect(`/jobs/${saved.id}`);
}

/** Moves a job to a new lifecycle state, stamping the first publication time. */
export async function changeJobStatus(id: string, status: JobStatus): Promise<void> {
  const current = await getJob(id);
  if (!current) notFound();

  await updateJob({
    ...current,
    status,
    publishedAt: status === "Published" ? (current.publishedAt ?? new Date().toISOString()) : current.publishedAt,
  });

  revalidatePath("/", "layout");
  redirect(`/jobs/${id}`);
}
