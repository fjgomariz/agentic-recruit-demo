"use server";

import { revalidatePath } from "next/cache";
import { notFound, redirect } from "next/navigation";
import type { Job, JobStatus } from "@domain";
import { ApiError, createJob, getJob, updateJob } from "@/data/jobs";
import { createJobId, readJobForm, validateJobForm, type JobFormState } from "@/lib/job-form";

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
