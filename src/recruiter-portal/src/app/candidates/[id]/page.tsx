import Link from "next/link";
import { notFound } from "next/navigation";
import { candidateDetails, jobs } from "@/data/mock-data";
import { Score, StatusBadge } from "@/components/ui";

export function generateStaticParams() { return candidateDetails.map(({ candidate }) => ({ id: candidate.id })); }

export default async function CandidateDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const details = candidateDetails.find(({ candidate }) => candidate.id === id);
  if (!details) notFound();
  const { candidate, application, resume, evaluation, report } = details;
  const job = jobs.find((item) => item.id === application.jobId);
  const name = `${candidate.firstName} ${candidate.lastName}`;

  return <>
    <Link href="/candidates" className="text-sm font-semibold text-cyan-700">← All candidates</Link>
    <div className="mt-5 flex flex-wrap items-center gap-4"><Score value={report.overallScore} /><div><h1 className="text-3xl font-bold tracking-tight">{name}</h1><p className="mt-1 text-slate-500">{job?.title} · {candidate.location}</p></div><div className="ml-auto"><StatusBadge status={evaluation.status} /></div></div>
    <div className="mt-7 grid gap-6 lg:grid-cols-[.8fr_1.4fr]">
      <aside className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Candidate profile</h2><dl className="mt-5 space-y-4 text-sm"><div><dt className="text-slate-500">Email</dt><dd className="mt-1 font-medium">{candidate.email}</dd></div><div><dt className="text-slate-500">Applied</dt><dd className="mt-1 font-medium">{new Date(application.appliedAt).toLocaleDateString()}</dd></div><div><dt className="text-slate-500">Current stage</dt><dd className="mt-1 font-medium">{application.stage}</dd></div><div><dt className="text-slate-500">Resume</dt><dd className="mt-1 font-medium">{resume.fileName}</dd></div></dl><h3 className="mt-8 font-bold">Recruiter feedback</h3><textarea className="mt-3 h-24 w-full rounded-lg border border-slate-200 p-3 text-sm" placeholder="Add private feedback…" /><button className="mt-3 w-full rounded-lg border border-slate-300 py-2.5 text-sm font-semibold">Save feedback</button></aside>
      <div className="space-y-6"><section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Resume summary</h2><p className="mt-4 leading-7 text-slate-700">{resume.summary}</p></section><section className="rounded-xl border border-cyan-100 bg-white p-6 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-sm font-semibold text-cyan-700">AI-generated evaluation report</p><h2 className="mt-1 text-xl font-bold">Suitability score: {report.overallScore}/100</h2></div><StatusBadge status={evaluation.status} /></div><p className="mt-5 font-medium text-slate-700">{report.recommendation}</p><div className="mt-6 grid gap-6 md:grid-cols-2"><div><h3 className="font-bold text-emerald-700">Strengths</h3><ul className="mt-3 space-y-2 text-sm text-slate-600">{report.strengths.map((item) => <li key={item}>✓ {item}</li>)}</ul></div><div><h3 className="font-bold text-amber-700">Considerations</h3><ul className="mt-3 space-y-2 text-sm text-slate-600">{report.considerations.map((item) => <li key={item}>• {item}</li>)}</ul></div></div><p className="mt-6 border-t border-slate-100 pt-4 text-xs text-slate-500">Execution {evaluation.agentExecutionId} · Human review required before progression</p></section></div>
    </div>
  </>;
}
