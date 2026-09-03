"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { CheckIcon, UploadIcon } from "@/components/icons";

export function ApplicationForm({ jobTitle }: { jobTitle: string }) {
  const [submitted, setSubmitted] = useState(false);
  const [fileName, setFileName] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (submitted) {
    return <div className="success-card"><span className="success-icon"><CheckIcon width={30} height={30} /></span><span className="eyebrow">Application received</span><h1>Thank you for applying.</h1><p>Your mock application for <strong>{jobTitle}</strong> has been recorded for this demo. No information was sent or stored.</p><Link className="button button-primary" href="/jobs">Explore more roles</Link></div>;
  }

  return (
    <form className="application-form" onSubmit={handleSubmit}>
      <div className="form-section"><div className="section-number">1</div><div className="form-section-content"><h2>Personal information</h2><p>Tell us how we can reach you.</p><div className="form-grid"><label>First name<span>*</span><input name="firstName" autoComplete="given-name" required /></label><label>Last name<span>*</span><input name="lastName" autoComplete="family-name" required /></label><label className="full-width">Email address<span>*</span><input name="email" type="email" autoComplete="email" required /></label><label className="full-width">Phone number<input name="phone" type="tel" autoComplete="tel" /></label></div></div></div>
      <div className="form-section"><div className="section-number">2</div><div className="form-section-content"><h2>Experience</h2><p>Share your background and professional profile.</p><div className="form-grid"><label className="full-width">LinkedIn or portfolio URL<input name="profile" type="url" placeholder="https://" /></label><label className="full-width">Resume<span>*</span><span className="upload-field"><UploadIcon /><strong>{fileName || "Choose a PDF or DOCX file"}</strong><small>Maximum file size: 5 MB</small><input aria-label="Upload resume" name="resume" type="file" accept=".pdf,.doc,.docx" required onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")} /></span></label></div></div></div>
      <div className="form-section"><div className="section-number">3</div><div className="form-section-content"><h2>A little more about you</h2><p>Help us understand what makes this opportunity interesting.</p><label>Why are you interested in this role?<span>*</span><textarea name="interest" rows={6} required placeholder="Share what excites you about the role and the impact you hope to make..." /></label></div></div>
      <div className="form-actions"><p>By submitting, you acknowledge this is a demonstration and no data will be stored.</p><button className="button button-primary" type="submit">Submit application</button></div>
    </form>
  );
}
