"use client";

import type { Job, JobApplication } from "@domain";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Avatar, StatusBadge, pendingEvaluation } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

export function CandidatesList({ applications, jobs }: { applications: JobApplication[]; jobs: Job[] }) {
  const [query, setQuery] = useState("");
  const [jobId, setJobId] = useState("all");
  const jobTitles = useMemo(() => new Map(jobs.map((job) => [job.id, job.title])), [jobs]);
  const jobsWithApplications = useMemo(() => jobs.filter((job) => applications.some((application) => application.jobId === job.id)), [jobs, applications]);

  const results = useMemo(() => {
    const term = query.trim().toLowerCase();
    return applications.filter((application) =>
      (jobId === "all" || application.jobId === jobId) &&
      (!term || application.candidateName.toLowerCase().includes(term) || application.candidateEmail.toLowerCase().includes(term)));
  }, [applications, query, jobId]);

  return <>
    <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-2">
      <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or email" aria-label="Search candidates" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-cyan-600" />
      <select value={jobId} onChange={(event) => setJobId(event.target.value)} aria-label="Filter by job" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm"><option value="all">All job postings</option>{jobsWithApplications.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select>
    </div>
    <p className="mt-5 text-sm text-slate-500">{results.length} {results.length === 1 ? "application" : "applications"} found</p>
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {results.length === 0 && <p className="p-8 text-center text-sm text-slate-500">{applications.length === 0 ? "No candidates have applied yet. Applications from the careers site appear here." : "No applications match your filters."}</p>}
      {results.map((application) => <div key={application.id} className="flex flex-wrap items-center gap-4 border-b border-slate-100 p-5 last:border-0 hover:bg-slate-50">
        <Avatar name={application.candidateName} />
        <div className="min-w-56 flex-1"><Link href={`/candidates/${application.id}`} className="font-semibold hover:text-cyan-700 hover:underline">{application.candidateName}</Link><p className="mt-1 text-sm text-slate-500">{application.candidateEmail}</p></div>
        <div className="min-w-48"><p className="text-xs text-slate-500">Applied for</p><Link href={`/jobs/${application.jobId}`} className="mt-1 block text-sm font-medium hover:text-cyan-700">{jobTitles.get(application.jobId) ?? application.jobId}</Link></div>
        <div className="min-w-36"><p className="text-xs text-slate-500">Submitted</p><p className="mt-1 text-sm">{formatDateTime(application.submittedAt)}</p></div>
        <div className="min-w-36"><p className="text-xs text-slate-500">Evaluation</p><div className="mt-1"><StatusBadge status={pendingEvaluation} /></div></div>
        <a href={`/applications/${application.id}/resume`} download={application.resumeFileName} className="text-sm font-semibold text-cyan-700 hover:underline">⬇ Resume</a>
      </div>)}
    </div>
  </>;
}
