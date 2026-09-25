"use client";

import { useActionState } from "react";
import Link from "next/link";
import type { Job } from "@domain";
import { saveJob } from "@/app/jobs/actions";
import { employmentTypes, experienceLevels, jobToFormValues, workplaceTypes, type JobFormField, type JobFormState } from "@/lib/job-form";

const inputClass = "mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-cyan-600 focus:outline-none focus:ring-2 focus:ring-cyan-100";

export function JobForm({ job }: { job?: Job }) {
  const [state, formAction, pending] = useActionState<JobFormState, FormData>(saveJob, {});
  const values = state.values ?? jobToFormValues(job);
  const errors = state.fieldErrors ?? {};

  const field = (name: JobFormField, label: string, options: { required?: boolean; hint?: string; placeholder?: string } = {}) => (
    <label className="block text-sm font-medium text-slate-700">
      {label}{options.required && <span className="text-rose-600"> *</span>}
      <input name={name} defaultValue={values[name]} placeholder={options.placeholder} aria-invalid={Boolean(errors[name])} className={inputClass} />
      {errors[name] ? <span className="mt-1 block text-xs text-rose-600">{errors[name]}</span> : options.hint && <span className="mt-1 block text-xs text-slate-500">{options.hint}</span>}
    </label>
  );

  const area = (name: JobFormField, label: string, rows: number, options: { required?: boolean; hint?: string } = {}) => (
    <label className="block text-sm font-medium text-slate-700">
      {label}{options.required && <span className="text-rose-600"> *</span>}
      <textarea name={name} rows={rows} defaultValue={values[name]} aria-invalid={Boolean(errors[name])} className={inputClass} />
      {errors[name] ? <span className="mt-1 block text-xs text-rose-600">{errors[name]}</span> : options.hint && <span className="mt-1 block text-xs text-slate-500">{options.hint}</span>}
    </label>
  );

  const select = (name: JobFormField, label: string, choices: string[]) => (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <select name={name} defaultValue={values[name]} className={inputClass}>{choices.map((choice) => <option key={choice}>{choice}</option>)}</select>
      {errors[name] && <span className="mt-1 block text-xs text-rose-600">{errors[name]}</span>}
    </label>
  );

  return (
    <form action={formAction} className="space-y-6">
      {job && <input type="hidden" name="id" value={job.id} />}
      {state.error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{state.error}</div>}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="font-bold">Role basics</h2>
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          {field("title", "Job title", { required: true, placeholder: "Senior Data Engineer" })}
          {field("department", "Department", { required: true, placeholder: "Engineering" })}
          {field("hiringManager", "Hiring manager", { required: true })}
          {select("experienceLevel", "Experience level", experienceLevels)}
          {select("employmentType", "Employment type", employmentTypes)}
          <label className="flex items-center gap-3 self-end pb-2 text-sm font-medium text-slate-700"><input type="checkbox" name="featured" defaultChecked={values.featured} className="h-4 w-4 rounded border-slate-300" />Feature on the careers home page</label>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="font-bold">Location</h2>
        <div className="mt-5 grid gap-5 md:grid-cols-3">
          {field("locationDisplayName", "Location", { required: true, placeholder: "London, UK" })}
          {select("workplaceType", "Workplace type", workplaceTypes)}
          {field("countryCode", "Country code", { hint: "Optional ISO code, for example GB", placeholder: "GB" })}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="font-bold">Description</h2>
        <div className="mt-5 space-y-5">
          {field("summary", "Candidate-facing summary", { required: true })}
          {area("description", "Full description", 5, { required: true })}
          <div className="grid gap-5 md:grid-cols-3">
            {area("responsibilities", "Responsibilities", 5, { required: true, hint: "One per line" })}
            {area("qualifications", "Required qualifications", 5, { required: true, hint: "One per line" })}
            {area("preferredQualifications", "Preferred qualifications", 5, { hint: "Optional, one per line" })}
          </div>
        </div>
      </section>

      <div className="flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-6">
        <Link href={job ? `/jobs/${job.id}` : "/jobs"} className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold">Cancel</Link>
        {job ? (
          <button type="submit" disabled={pending} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{pending ? "Saving…" : "Save changes"}</button>
        ) : (
          <>
            <button type="submit" name="intent" value="draft" disabled={pending} className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold disabled:opacity-60">Save as draft</button>
            <button type="submit" name="intent" value="submit" disabled={pending} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{pending ? "Saving…" : "Submit for approval"}</button>
          </>
        )}
      </div>
    </form>
  );
}
