import type { AgentExecution, AgentFeedback, AiAssessmentRating, Job, JobApplication } from "@domain";

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

/** Retrieves a job's candidate applications, newest first. */
export async function getJobApplications(jobId: string): Promise<JobApplication[]> {
  const response = await fetch(`${apiBaseUrl}/jobs/${encodeURIComponent(jobId)}/applications`, { cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to retrieve applications: ${response.status}`);
  return (await response.json()) as JobApplication[];
}

/** Retrieves every candidate application across jobs, newest first. */
export async function getApplications(): Promise<JobApplication[]> {
  const response = await fetch(`${apiBaseUrl}/applications`, { cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to retrieve applications: ${response.status}`);
  return (await response.json()) as JobApplication[];
}

/** Retrieves one candidate application. */
export async function getApplication(id: string): Promise<JobApplication | undefined> {
  const response = await fetch(`${apiBaseUrl}/applications/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (response.status === 404) return undefined;
  if (!response.ok) throw await readError(response, `Failed to retrieve application '${id}': ${response.status}`);
  return (await response.json()) as JobApplication;
}

/** Starts (or restarts) the AI assessment of an application; evaluation and review complete in the background. */
export async function evaluateApplication(id: string): Promise<JobApplication> {
  const response = await fetch(`${apiBaseUrl}/applications/${encodeURIComponent(id)}/evaluation`, { method: "POST", cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to start the evaluation: ${response.status}`);
  return (await response.json()) as JobApplication;
}

/** Re-runs only the reviewer agent on the current evaluation. */
export async function reviewApplication(id: string): Promise<JobApplication> {
  const response = await fetch(`${apiBaseUrl}/applications/${encodeURIComponent(id)}/review`, { method: "POST", cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to start the review: ${response.status}`);
  return (await response.json()) as JobApplication;
}

/** Records the recruiter's approval decision, rating of the AI assessment, and feedback for the agents. */
export async function decideApplication(id: string, decision: { status: "Advanced" | "Rejected"; comment: string; decidedBy: string; aiRating: AiAssessmentRating | null; agentFeedback: string }): Promise<JobApplication> {
  const response = await fetch(`${apiBaseUrl}/applications/${encodeURIComponent(id)}/decision`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(decision),
    cache: "no-store",
  });
  if (!response.ok) throw await readError(response, `Failed to record the decision: ${response.status}`);
  return (await response.json()) as JobApplication;
}

/** Clears the recruiter's decision so it can be made again. */
export async function clearApplicationDecision(id: string): Promise<JobApplication> {
  const response = await fetch(`${apiBaseUrl}/applications/${encodeURIComponent(id)}/decision`, { method: "DELETE", cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to clear the decision: ${response.status}`);
  return (await response.json()) as JobApplication;
}

/** Retrieves recent Foundry agent runs recorded by the API. */
export async function getAgentExecutions(limit = 50): Promise<AgentExecution[]> {
  const response = await fetch(`${apiBaseUrl}/agent-executions?limit=${limit}`, { cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to retrieve agent runs: ${response.status}`);
  return (await response.json()) as AgentExecution[];
}

/** Retrieves recruiter feedback on the AI workflow (no candidate personal data). */
export async function getAgentFeedback(): Promise<AgentFeedback[]> {
  const response = await fetch(`${apiBaseUrl}/agent-feedback`, { cache: "no-store" });
  if (!response.ok) throw await readError(response, `Failed to retrieve agent feedback: ${response.status}`);
  return (await response.json()) as AgentFeedback[];
}

/** Streams an application's stored PDF resume from the API. */
export async function downloadResume(applicationId: string): Promise<Response> {
  return fetch(`${apiBaseUrl}/applications/${encodeURIComponent(applicationId)}/resume`, { cache: "no-store" });
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
