import type { Job } from "./job";

/** Current workflow stage of a submitted candidate application. */
export type ApplicationStage = "AI review" | "Recruiter review" | "Hiring manager review" | "Closed";

/** Lifecycle state of a candidate application. */
export type ApplicationStatus = "Submitted" | "In review" | "Advanced" | "Rejected" | "Withdrawn";

/** Person who may submit one or more applications to jobs. */
export interface Candidate {
  /** Stable candidate identifier. */
  id: string;
  /** Candidate's given name. */
  firstName: string;
  /** Candidate's family name. */
  lastName: string;
  /** Candidate contact email. */
  email: string;
  /** Human-readable candidate location. */
  location: string;
  /** Optional professional profile or portfolio URL. */
  profileUrl?: string;
}

/** Resume document and extracted demo metadata owned by a candidate. */
export interface Resume {
  /** Stable resume identifier. */
  id: string;
  /** Candidate who owns this resume. */
  candidateId: Candidate["id"];
  /** Original uploaded file name. */
  fileName: string;
  /** MIME type of the uploaded document. */
  contentType: string;
  /** Blob or document reference; never the document content itself. */
  storageReference: string;
  /** Agent- or recruiter-produced summary of relevant experience. */
  summary?: string;
  /** ISO 8601 upload timestamp. */
  uploadedAt: string;
}

/** Candidate's submission for one specific job. */
export interface CandidateApplication {
  /** Stable application identifier. */
  id: string;
  /** Candidate making the application. */
  candidateId: Candidate["id"];
  /** Job to which the candidate applied. */
  jobId: Job["id"];
  /** Resume submitted with this application. */
  resumeId: Resume["id"];
  /** Current business stage of the application. */
  stage: ApplicationStage;
  /** Current lifecycle status of the application. */
  status: ApplicationStatus;
  /** Candidate-provided interest statement. */
  interestStatement?: string;
  /** ISO 8601 submission timestamp. */
  appliedAt: string;
  /** Evaluation associated with this application, when available. */
  evaluationId?: string;
}
