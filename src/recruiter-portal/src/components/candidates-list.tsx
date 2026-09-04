"use client";

import type { Job } from "@domain";
import Link from "next/link";
import { useMemo, useState } from "react";
import { candidateDetails as mockCandidateDetails } from "@/data/mock-data";
import { Score, StatusBadge } from "@/components/ui";

type CandidateDetails = typeof mockCandidateDetails;

function candidateName(firstName: string, lastName: string) { return `${firstName} ${lastName}`; }

export function CandidatesList({ candidateDetails, jobs }: { candidateDetails: CandidateDetails; jobs: Job[] }) {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("all");
  const [status, setStatus] = useState("all");
  const results = useMemo(() => candidateDetails.filter(({ candidate, application, evaluation }) => {
    const name = candidateName(candidate.firstName, candidate.lastName);
    return (role === "all" || application.jobId === role) && (status === "all" || evaluation.status === status) && name.toLowerCase().includes(query.toLowerCase());
  }), [candidateDetails, query, role, status]);

  return <>
    <div className="mb-8"><p className="text-sm font-medium text-cyan-700">Candidate review</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Candidates</h1><p className="mt-2 text-slate-500">Review AI-assisted assessments and retain control over every decision.</p></div>
    <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-3"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search candidates" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-cyan-600" /><select value={role} onChange={(event) => setRole(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm"><option value="all">All job postings</option>{jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select><select value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm"><option value="all">All evaluation statuses</option><option>Completed</option><option>Needs review</option></select></div>
    <p className="mt-5 text-sm text-slate-500">{results.length} candidates found</p>
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">{results.map(({ candidate, application, evaluation, report }) => <Link href={`/candidates/${candidate.id}`} key={candidate.id} className="flex flex-wrap items-center gap-4 border-b border-slate-100 p-5 last:border-0 hover:bg-slate-50"><Score value={report.overallScore} /><div className="min-w-45 flex-1"><p className="font-semibold">{candidateName(candidate.firstName, candidate.lastName)}</p><p className="mt-1 text-sm text-slate-500">{candidate.location} · Applied {new Date(application.appliedAt).toLocaleDateString()}</p></div><div className="min-w-40"><p className="text-xs text-slate-500">Evaluation</p><div className="mt-1"><StatusBadge status={evaluation.status} /></div></div><div className="min-w-35"><p className="text-xs text-slate-500">Stage</p><p className="mt-1 text-sm font-medium">{application.stage}</p></div></Link>)}</div>
  </>;
}