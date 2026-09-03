/** Lifecycle state of a job posting. */
export type JobStatus = "Draft" | "Pending Approval" | "Published" | "Closed";

/** Supported work arrangements for a job. */
export type WorkplaceType = "Remote" | "Hybrid" | "On-site";

/** Contractual employment arrangement offered by a job. */
export type EmploymentType = "Full-time" | "Part-time" | "Contract" | "Internship";

/** Expected career level for a job. */
export type ExperienceLevel = "Entry" | "Mid" | "Senior" | "Lead" | "Executive";

/** Structured location and work-arrangement information for a job. */
export interface JobLocation {
  /** Human-readable location used by the portals. */
  displayName: string;
  /** Work arrangement associated with the location. */
  workplaceType: WorkplaceType;
  /** ISO 3166-1 alpha-2 country code when known. */
  countryCode?: string;
}

/** Canonical job posting shared by candidate, recruiter, agent, and persistence flows. */
export interface Job {
  /** Stable job identifier and route key. */
  id: string;
  /** Candidate-facing title of the role. */
  title: string;
  /** Owning team or department. */
  department: string;
  /** Structured location of the role. */
  location: JobLocation;
  /** Current publishing lifecycle state. */
  status: JobStatus;
  /** Employment arrangement for the role. */
  employmentType: EmploymentType;
  /** Expected candidate experience level. */
  experienceLevel: ExperienceLevel;
  /** Short candidate-facing summary. */
  summary: string;
  /** Full approved or proposed job description. */
  description: string;
  /** Primary outcomes and duties of the role. */
  responsibilities: string[];
  /** Required candidate qualifications. */
  qualifications: string[];
  /** Optional qualifications that strengthen an application. */
  preferredQualifications: string[];
  /** Display name of the accountable hiring manager. */
  hiringManager: string;
  /** ISO 8601 timestamp at which the job was created. */
  createdAt: string;
  /** ISO 8601 timestamp at which the job was published, when applicable. */
  publishedAt?: string;
  /** Number of applications, maintained here only for the demo UI. */
  applicantCount: number;
  /** Whether the public portal should promote the role. */
  featured?: boolean;
  /** Agent execution that proposed the description, when AI-assisted. */
  authoringExecutionId?: string;
}
