import type { Job } from "./job";

/** Application submitted through the public portal, stored in Cosmos DB with its resume in Blob Storage. */
export interface JobApplication {
  /** Generated application identifier; also names the resume blob. */
  id: string;
  /** Job the candidate applied for. */
  jobId: Job["id"];
  /** Candidate's full name. */
  candidateName: string;
  /** Candidate contact email. */
  candidateEmail: string;
  /** Optional short message from the candidate. */
  message: string;
  /** Original name of the uploaded PDF. */
  resumeFileName: string;
  /** Resume location as `<container>/<blob>`. */
  resumeBlobPath: string;
  /** ISO 8601 submission timestamp. */
  submittedAt: string;
}
