"use client";

import { useActionState, useState } from "react";
import Link from "next/link";
import { applyForJob, type ApplicationFormState } from "@/app/jobs/[id]/apply/actions";
import { CheckIcon, UploadIcon } from "@/components/icons";

export function ApplicationForm({ jobId, jobTitle }: { jobId: string; jobTitle: string }) {
  const [state, formAction, pending] = useActionState<ApplicationFormState, FormData>(applyForJob.bind(null, jobId), {});
  const [fileName, setFileName] = useState("");

  // The browser clears the file input after every submission, so clear its label too.
  const [syncedState, setSyncedState] = useState(state);
  if (state !== syncedState) {
    setSyncedState(state);
    setFileName("");
  }

  if (state.submitted) {
    return (
      <div className="success-card" role="status">
        <span className="success-icon"><CheckIcon width={30} height={30} /></span>
        <span className="eyebrow">Application received</span>
        <h1>Thank you for applying.</h1>
        <p>Your application for <strong>{jobTitle}</strong> and your resume have been received. Our recruiting team will contact you at <strong>{state.submitted.candidateEmail}</strong>.</p>
        <p className="application-reference">Reference {state.submitted.id}</p>
        <Link className="button button-primary" href="/jobs">Explore more roles</Link>
      </div>
    );
  }

  const values = state.values;

  return (
    <form className="application-form" action={formAction}>
      {state.error && <div className="form-error" role="alert">{state.error}</div>}
      <div className="form-section"><div className="section-number">1</div><div className="form-section-content"><h2>Your details</h2><p>Tell us who you are and how we can reach you.</p><div className="form-grid">
        <label className="full-width">Full name<span>*</span><input name="candidateName" autoComplete="name" required maxLength={120} defaultValue={values?.candidateName} /></label>
        <label className="full-width">Email address<span>*</span><input name="candidateEmail" type="email" autoComplete="email" required maxLength={254} defaultValue={values?.candidateEmail} /></label>
      </div></div></div>
      <div className="form-section"><div className="section-number">2</div><div className="form-section-content"><h2>Resume</h2><p>Upload your resume as a PDF.</p>
        <label>Resume<span>*</span><span className="upload-field"><UploadIcon /><strong>{fileName || "Choose a PDF file"}</strong><small>PDF only · Maximum file size: 5 MB</small><input aria-label="Upload resume" name="resume" type="file" accept="application/pdf,.pdf" required onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")} /></span></label>
      </div></div>
      <div className="form-section"><div className="section-number">3</div><div className="form-section-content"><h2>A short message</h2><p>Optional: tell us why this role interests you.</p>
        <label>Message<textarea name="message" rows={5} maxLength={2000} defaultValue={values?.message} placeholder="Share what excites you about the role..." /></label>
      </div></div>
      <div className="form-actions"><p>Your details and resume are stored securely and only shared with the recruiting team for this role.</p><button className="button button-primary" type="submit" disabled={pending}>{pending ? "Submitting…" : "Submit application"}</button></div>
    </form>
  );
}
