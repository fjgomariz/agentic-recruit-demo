import type { Job } from "@domain";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

/** Retrieves published jobs from the backend API. */
export async function getJobs(): Promise<Job[]> {
  const response = await fetch(`${apiBaseUrl}/jobs`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Failed to retrieve jobs: ${response.status}`);
  const jobs = (await response.json()) as Job[];
  return jobs.filter((job) => job.status === "Published");
}

/** Retrieves one published job from the backend API. */
export async function getJob(id: string): Promise<Job | undefined> {
  const response = await fetch(`${apiBaseUrl}/jobs/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (response.status === 404) return undefined;
  if (!response.ok) throw new Error(`Failed to retrieve Job '${id}': ${response.status}`);
  const job = (await response.json()) as Job;
  return job.status === "Published" ? job : undefined;
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
