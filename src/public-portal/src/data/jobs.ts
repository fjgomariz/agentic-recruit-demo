import type { Job } from "@domain";
import { publicJobs } from "@mocks";

/** Candidate-visible jobs sourced from the shared canonical mock records. */
export const jobs: Job[] = publicJobs;

/** Finds a candidate-visible job by its stable identifier. */
export function getJob(id: string): Job | undefined {
  return jobs.find((job) => job.id === id);
}

/** Formats a publication timestamp for compact candidate-facing display. */
export function getPublishedLabel(job: Job): string {
  if (!job.publishedAt) return "Recently posted";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(job.publishedAt));
}
