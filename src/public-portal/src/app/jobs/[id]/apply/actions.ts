"use server";

import { ApiError, submitApplication } from "@/data/jobs";

const maxResumeBytes = 5 * 1024 * 1024;

export interface ApplicationFormValues {
  candidateName: string;
  candidateEmail: string;
  message: string;
}

/** Outcome of an application submission returned to the form. */
export interface ApplicationFormState {
  values?: ApplicationFormValues;
  error?: string;
  submitted?: { id: string; candidateEmail: string };
}

/** Validates the form, then uploads the resume and creates the application through the API. */
export async function applyForJob(jobId: string, _: ApplicationFormState, formData: FormData): Promise<ApplicationFormState> {
  const values: ApplicationFormValues = {
    candidateName: String(formData.get("candidateName") ?? "").trim(),
    candidateEmail: String(formData.get("candidateEmail") ?? "").trim(),
    message: String(formData.get("message") ?? "").trim(),
  };
  const resume = formData.get("resume");

  if (!values.candidateName) return { values, error: "Enter your name." };
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(values.candidateEmail)) return { values, error: "Enter a valid email address." };
  if (!(resume instanceof File) || resume.size === 0) return { values, error: "Attach your resume as a PDF file." };
  if (!resume.name.toLowerCase().endsWith(".pdf")) return { values, error: "Your resume must be a PDF file." };
  if (resume.size > maxResumeBytes) return { values, error: "Your resume must be 5 MB or smaller." };

  try {
    const application = await submitApplication(jobId, { ...values, resume });
    return { submitted: { id: application.id, candidateEmail: application.candidateEmail } };
  } catch (error) {
    return { values, error: error instanceof ApiError ? error.message : "We could not submit your application. Please try again." };
  }
}
