import type { Job } from "@domain";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

/** Retrieves all jobs from the backend API. */
export async function getJobs(): Promise<Job[]> {
  const response = await fetch(`${apiBaseUrl}/jobs`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Failed to retrieve jobs: ${response.status}`);
  return (await response.json()) as Job[];
}

/** Retrieves one job from the backend API. */
export async function getJob(id: string): Promise<Job | undefined> {
  const response = await fetch(`${apiBaseUrl}/jobs/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (response.status === 404) return undefined;
  if (!response.ok) throw new Error(`Failed to retrieve Job '${id}': ${response.status}`);
  return (await response.json()) as Job;
}