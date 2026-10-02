"use client";

import { useActionState, useRef, useState, useTransition } from "react";
import Link from "next/link";
import type { Job } from "@domain";
import { generateJobDescription, saveJob } from "@/app/jobs/actions";
import { employmentTypes, experienceLevels, jobToFormValues, workplaceTypes, type JobFormField, type JobFormState, type JobFormValues } from "@/lib/job-form";

const inputClass = "mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-cyan-600 focus:outline-none focus:ring-2 focus:ring-cyan-100";

const contentFields = ["summary", "description", "responsibilities", "qualifications", "preferredQualifications", "authoringExecutionId"] as const;
type ContentField = (typeof contentFields)[number];
type Content = Record<ContentField, string>;

const pickContent = (values: JobFormValues): Content => Object.fromEntries(contentFields.map((field) => [field, values[field]])) as Content;
const formValue = (form: HTMLFormElement | null, name: string) => String(new FormData(form ?? undefined).get(name) ?? "").trim();

function SparkIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M12 2l1.8 5.6L19.5 9l-5.7 1.6L12 16l-1.8-5.4L4.5 9l5.7-1.4L12 2zm6.5 11l.9 2.6 2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.6z" /></svg>;
}

export function JobForm({ job }: { job?: Job }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [state, formAction, pending] = useActionState<JobFormState, FormData>(saveJob, {});
  const [generating, startGenerating] = useTransition();
  const initialValues = jobToFormValues(job);
  const values = state.values ?? initialValues;
  const errors = state.fieldErrors ?? {};

  const [content, setContent] = useState<Content>(() => pickContent(values));
  const [notes, setNotes] = useState(values.aiNotes);
  const [showContent, setShowContent] = useState(Boolean(job) || Boolean(values.description));
  const [generationError, setGenerationError] = useState<string>();
  const [lastRun, setLastRun] = useState<string>();

  // A failed save returns the submitted values; resync controlled fields with them.
  const [syncedState, setSyncedState] = useState(state);
  if (state !== syncedState) {
    setSyncedState(state);
    if (state.values) {
      setContent(pickContent(state.values));
      setNotes(state.values.aiNotes);
      if (state.values.description || state.fieldErrors?.description) setShowContent(true);
    }
  }

  const generate = () => {
    const form = formRef.current;
    setGenerationError(undefined);
    startGenerating(async () => {
      const outcome = await generateJobDescription({
        title: formValue(form, "title"),
        department: formValue(form, "department") || undefined,
        location: formValue(form, "locationDisplayName") || undefined,
        workplaceType: formValue(form, "workplaceType") || undefined,
        employmentType: formValue(form, "employmentType") || undefined,
        experienceLevel: formValue(form, "experienceLevel") || undefined,
        hiringManager: formValue(form, "hiringManager") || undefined,
        notes,
      });
      if (outcome.error !== undefined) {
        setGenerationError(outcome.error);
        return;
      }
      const { draft, executionId, agentVersion } = outcome.result;
      setContent({
        summary: draft.summary,
        description: draft.description,
        responsibilities: draft.responsibilities.join("\n"),
        qualifications: draft.qualifications.join("\n"),
        preferredQualifications: draft.preferredQualifications.join("\n"),
        authoringExecutionId: executionId,
      });
      setLastRun(agentVersion ? `${executionId} · agent v${agentVersion}` : executionId);
      setShowContent(true);
    });
  };

  const fieldError = (name: JobFormField, hint?: string) => errors[name] ? <span className="mt-1 block text-xs text-rose-600">{errors[name]}</span> : hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>;

  const field = (name: JobFormField, label: string, options: { required?: boolean; hint?: string; placeholder?: string } = {}) => (
    <label className="block text-sm font-medium text-slate-700">
      {label}{options.required && <span className="text-rose-600"> *</span>}
      <input name={name} defaultValue={values[name]} placeholder={options.placeholder} aria-invalid={Boolean(errors[name])} className={inputClass} />
      {fieldError(name, options.hint)}
    </label>
  );

  const select = (name: JobFormField, label: string, choices: string[]) => (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <select name={name} defaultValue={values[name]} className={inputClass}>{choices.map((choice) => <option key={choice}>{choice}</option>)}</select>
      {fieldError(name)}
    </label>
  );

  const contentInput = (name: Exclude<ContentField, "authoringExecutionId">, label: string, rows: number, options: { required?: boolean; hint?: string } = {}) => (
    <label className="block text-sm font-medium text-slate-700">
      {label}{options.required && <span className="text-rose-600"> *</span>}
      {rows === 1
        ? <input name={name} value={content[name]} onChange={(event) => setContent({ ...content, [name]: event.target.value })} aria-invalid={Boolean(errors[name])} className={inputClass} />
        : <textarea name={name} rows={rows} value={content[name]} onChange={(event) => setContent({ ...content, [name]: event.target.value })} aria-invalid={Boolean(errors[name])} className={inputClass} />}
      {fieldError(name, options.hint)}
    </label>
  );

  return (
    <form ref={formRef} action={formAction} className="space-y-6">
      {job && <input type="hidden" name="id" value={job.id} />}
      <input type="hidden" name="authoringExecutionId" value={content.authoringExecutionId} />
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

      <section className="rounded-xl border border-cyan-100 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="font-bold">Job description</h2><p className="mt-1 text-sm text-slate-500">Describe the role in your own words. The job description agent drafts the full posting from these notes and the role basics above.</p></div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-700"><SparkIcon />Foundry agent</span>
        </div>
        <label className="mt-5 block text-sm font-medium text-slate-700">
          What should this role achieve, and who are you looking for?
          <textarea name="aiNotes" rows={5} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Small platform team, migrating to Azure Container Apps. Needs strong Bicep and CI/CD, has mentored engineers. Nice to have: Cosmos DB." className={inputClass} />
        </label>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" onClick={generate} disabled={generating || pending} className="inline-flex items-center gap-2 rounded-lg bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">
            <SparkIcon />{generating ? "Generating…" : content.description ? "Regenerate with AI" : "Generate with AI"}
          </button>
          {!showContent && <button type="button" onClick={() => setShowContent(true)} className="text-sm font-semibold text-slate-600 hover:text-slate-900">Write it manually instead</button>}
          {generating && <span role="status" className="text-sm text-slate-500">The agent is drafting the posting. This usually takes a few seconds.</span>}
        </div>
        {generationError && <div role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{generationError}</div>}

        {showContent ? (
          <div className="mt-6 space-y-5 border-t border-slate-100 pt-6">
            {lastRun && <p className="rounded-lg bg-cyan-50 px-4 py-3 text-sm text-cyan-800">AI draft ready. Review and edit it before saving. <span className="text-xs text-cyan-700">Run {lastRun}</span></p>}
            {contentInput("summary", "Candidate-facing summary", 1, { required: true })}
            {contentInput("description", "Full description", 8, { required: true })}
            <div className="grid gap-5 md:grid-cols-3">
              {contentInput("responsibilities", "Responsibilities", 7, { required: true, hint: "One per line" })}
              {contentInput("qualifications", "Required qualifications", 7, { required: true, hint: "One per line" })}
              {contentInput("preferredQualifications", "Preferred qualifications", 7, { hint: "Optional, one per line" })}
            </div>
          </div>
        ) : (
          (errors.description || errors.summary) && <p className="mt-4 text-sm text-rose-600">Generate the description with AI or write it manually before saving.</p>
        )}
      </section>

      <div className="flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-6">
        <Link href={job ? `/jobs/${job.id}` : "/jobs"} className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold">Cancel</Link>
        {job ? (
          <button type="submit" disabled={pending || generating} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{pending ? "Saving…" : "Save changes"}</button>
        ) : (
          <>
            <button type="submit" name="intent" value="draft" disabled={pending || generating} className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold disabled:opacity-60">Save as draft</button>
            <button type="submit" name="intent" value="submit" disabled={pending || generating} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{pending ? "Saving…" : "Submit for approval"}</button>
          </>
        )}
      </div>
    </form>
  );
}
