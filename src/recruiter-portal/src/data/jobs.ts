import type { Job } from "@domain";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

/** Error returned by the backend API with its HTTP status and detail message. */
export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function readError(response: Response, fallback: string): Promise<ApiError> {
  let detail = fallback;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
    else if (Array.isArray(body.detail)) detail = body.detail.map((item: { loc?: unknown[]; msg?: string }) => `${(item.loc ?? []).slice(1).join(".")}: ${item.msg}`).join("; ");
  } catch {
    // Keep the fallback when the API does not return JSON.
  }
  return new ApiError(response.status, detail);
}

/** Retrieves all jobs stored in Cosmos DB through the backend API. */
export async function getJobs(): Promise<Job[]> {
  const response = await fetch(`${apiBaseUrl}/jobs`, { cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to retrieve jobs: ${response.status}`);
  return (await response.json()) as Job[];
}

/** Retrieves one job from the backend API. */
export async function getJob(id: string): Promise<Job | undefined> {
  const response = await fetch(`${apiBaseUrl}/jobs/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (response.status === 404) return undefined;
  if (!response.ok) throw await readError(response, `Failed to retrieve Job '${id}': ${response.status}`);
  return (await response.json()) as Job;
}

/** Creates a job in Cosmos DB through the backend API. */
export async function createJob(job: Job): Promise<Job> {
  const response = await fetch(`${apiBaseUrl}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(job),
    cache: "no-store",
  });
  if (!response.ok) throw await readError(response, `Failed to create Job: ${response.status}`);
  return (await response.json()) as Job;
}

/** Replaces a job in Cosmos DB through the backend API. */
export async function updateJob(job: Job): Promise<Job> {
  const response = await fetch(`${apiBaseUrl}/jobs/${encodeURIComponent(job.id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(job),
    cache: "no-store",
  });
  if (!response.ok) throw await readError(response, `Failed to update Job '${job.id}': ${response.status}`);
  return (await response.json()) as Job;
}

/** Role facts and recruiter notes sent to the job description agent. */
export interface JobDescriptionRequest {
  title: string;
  department?: string;
  location?: string;
  workplaceType?: string;
  employmentType?: string;
  experienceLevel?: string;
  hiringManager?: string;
  notes: string;
}

/** Candidate-facing job content proposed by the agent. */
export type JobDescriptionDraft = Pick<Job, "summary" | "description" | "responsibilities" | "qualifications" | "preferredQualifications">;

/** Agent draft plus the identifier of the Foundry response that produced it. */
export interface JobDescriptionDraftResult {
  draft: JobDescriptionDraft;
  executionId: string;
  agentName: string;
  agentVersion?: string | null;
}

/** Asks the Foundry job description agent, through the API, for a draft posting. */
export async function draftJobDescription(request: JobDescriptionRequest): Promise<JobDescriptionDraftResult> {
  const response = await fetch(`${apiBaseUrl}/job-description-drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    cache: "no-store",
    signal: AbortSignal.timeout(90_000),
  });
  if (!response.ok) throw await readError(response, `Failed to generate a job description: ${response.status}`);
  return (await response.json()) as JobDescriptionDraftResult;
}
