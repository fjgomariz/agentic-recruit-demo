import type { Job, JobApplication } from "@domain";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

/** Error returned by the backend API with its HTTP status and readable detail. */
export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

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

/** Sends the application and PDF resume to the API, which stores them in Cosmos DB and Blob Storage. */
export async function submitApplication(jobId: string, application: { candidateName: string; candidateEmail: string; message: string; resume: File }): Promise<JobApplication> {
  const body = new FormData();
  body.set("candidateName", application.candidateName);
  body.set("candidateEmail", application.candidateEmail);
  body.set("message", application.message);
  body.set("resume", application.resume, application.resume.name);

  const response = await fetch(`${apiBaseUrl}/jobs/${encodeURIComponent(jobId)}/applications`, { method: "POST", body, cache: "no-store" });
  if (!response.ok) {
    let detail = `The application could not be submitted (${response.status}).`;
    try {
      const error = (await response.json()) as { detail?: unknown };
      if (typeof error.detail === "string") detail = error.detail;
    } catch {
      // Keep the generic message when the API does not return JSON.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as JobApplication;
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
