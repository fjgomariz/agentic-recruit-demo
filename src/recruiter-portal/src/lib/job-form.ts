import type { EmploymentType, ExperienceLevel, Job, WorkplaceType } from "@domain";

export const workplaceTypes: WorkplaceType[] = ["Remote", "Hybrid", "On-site"];
export const employmentTypes: EmploymentType[] = ["Full-time", "Part-time", "Contract", "Internship"];
export const experienceLevels: ExperienceLevel[] = ["Entry", "Mid", "Senior", "Lead", "Executive"];

export const jobFormFields = [
  "title",
  "department",
  "locationDisplayName",
  "workplaceType",
  "countryCode",
  "employmentType",
  "experienceLevel",
  "hiringManager",
  "summary",
  "description",
  "responsibilities",
  "qualifications",
  "preferredQualifications",
] as const;

export type JobFormField = (typeof jobFormFields)[number];
export type JobFormValues = Record<JobFormField, string> & { featured: boolean };
export type JobFormErrors = Partial<Record<JobFormField, string>>;

/** Result returned by the save action to the job form. */
export interface JobFormState {
  values?: JobFormValues;
  fieldErrors?: JobFormErrors;
  error?: string;
}

/** Recruiter-editable job fields; identity, lifecycle, and counters are managed by the portal. */
export type JobContent = Pick<
  Job,
  | "title"
  | "department"
  | "location"
  | "employmentType"
  | "experienceLevel"
  | "hiringManager"
  | "summary"
  | "description"
  | "responsibilities"
  | "qualifications"
  | "preferredQualifications"
  | "featured"
>;

const requiredFields: JobFormField[] = ["title", "department", "locationDisplayName", "hiringManager", "summary", "description"];

function toLines(value: string): string[] {
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

/** Maps an existing job, or sensible defaults, to form values. */
export function jobToFormValues(job?: Job): JobFormValues {
  return {
    title: job?.title ?? "",
    department: job?.department ?? "",
    locationDisplayName: job?.location.displayName ?? "",
    workplaceType: job?.location.workplaceType ?? "Hybrid",
    countryCode: job?.location.countryCode ?? "",
    employmentType: job?.employmentType ?? "Full-time",
    experienceLevel: job?.experienceLevel ?? "Mid",
    hiringManager: job?.hiringManager ?? "",
    summary: job?.summary ?? "",
    description: job?.description ?? "",
    responsibilities: (job?.responsibilities ?? []).join("\n"),
    qualifications: (job?.qualifications ?? []).join("\n"),
    preferredQualifications: (job?.preferredQualifications ?? []).join("\n"),
    featured: job?.featured ?? false,
  };
}

/** Reads submitted job form values without interpreting them. */
export function readJobForm(formData: FormData): JobFormValues {
  const values = Object.fromEntries(jobFormFields.map((field) => [field, String(formData.get(field) ?? "").trim()])) as Record<JobFormField, string>;
  return { ...values, featured: formData.get("featured") === "on" };
}

/** Validates form values and converts them to job content. */
export function validateJobForm(values: JobFormValues): { content?: JobContent; fieldErrors: JobFormErrors } {
  const fieldErrors: JobFormErrors = {};
  for (const field of requiredFields) if (!values[field]) fieldErrors[field] = "Required";
  if (!workplaceTypes.includes(values.workplaceType as WorkplaceType)) fieldErrors.workplaceType = "Choose a workplace type";
  if (!employmentTypes.includes(values.employmentType as EmploymentType)) fieldErrors.employmentType = "Choose an employment type";
  if (!experienceLevels.includes(values.experienceLevel as ExperienceLevel)) fieldErrors.experienceLevel = "Choose an experience level";
  if (values.countryCode && !/^[A-Za-z]{2}$/.test(values.countryCode)) fieldErrors.countryCode = "Use a two-letter code, for example GB";

  const responsibilities = toLines(values.responsibilities);
  const qualifications = toLines(values.qualifications);
  if (responsibilities.length === 0) fieldErrors.responsibilities = "Add at least one responsibility";
  if (qualifications.length === 0) fieldErrors.qualifications = "Add at least one qualification";
  if (Object.keys(fieldErrors).length > 0) return { fieldErrors };

  return {
    fieldErrors,
    content: {
      title: values.title,
      department: values.department,
      location: {
        displayName: values.locationDisplayName,
        workplaceType: values.workplaceType as WorkplaceType,
        ...(values.countryCode ? { countryCode: values.countryCode.toUpperCase() } : {}),
      },
      employmentType: values.employmentType as EmploymentType,
      experienceLevel: values.experienceLevel as ExperienceLevel,
      hiringManager: values.hiringManager,
      summary: values.summary,
      description: values.description,
      responsibilities,
      qualifications,
      preferredQualifications: toLines(values.preferredQualifications),
      featured: values.featured,
    },
  };
}

/** Creates a readable, collision-resistant job identifier from its title. */
export function createJobId(title: string): string {
  const slug = title
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/, "");
  return `${slug || "job"}-${crypto.randomUUID().slice(0, 6)}`;
}
