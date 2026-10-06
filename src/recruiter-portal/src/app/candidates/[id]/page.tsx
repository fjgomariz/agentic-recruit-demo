import Link from "next/link";
import { notFound } from "next/navigation";
import { Avatar, StatusBadge, pendingEvaluation } from "@/components/ui";
import { getApplication, getJob } from "@/data/jobs";
import { formatDateTime } from "@/lib/format";

export default async function CandidateDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const application = await getApplication(id);
  if (!application) notFound();
  const job = await getJob(application.jobId);

  return <>
    <Link href="/candidates" className="text-sm font-semibold text-cyan-700">← All candidates</Link>
    <div className="mt-5 flex flex-wrap items-center gap-4"><Avatar name={application.candidateName} /><div><h1 className="text-3xl font-bold tracking-tight">{application.candidateName}</h1><p className="mt-1 text-slate-500">Applied for {job ? <Link href={`/jobs/${job.id}`} className="font-medium text-cyan-700 hover:underline">{job.title}</Link> : application.jobId}</p></div><div className="ml-auto"><StatusBadge status={pendingEvaluation} /></div></div>
    <div className="mt-7 grid gap-6 lg:grid-cols-[.8fr_1.4fr]">
      <aside className="h-fit rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="font-bold">Application</h2>
        <dl className="mt-5 space-y-4 text-sm">
          <div><dt className="text-slate-500">Email</dt><dd className="mt-1 font-medium"><a className="text-cyan-700 hover:underline" href={`mailto:${application.candidateEmail}`}>{application.candidateEmail}</a></dd></div>
          <div><dt className="text-slate-500">Submitted</dt><dd className="mt-1 font-medium">{formatDateTime(application.submittedAt)}</dd></div>
          <div><dt className="text-slate-500">Job status</dt><dd className="mt-1">{job ? <StatusBadge status={job.status} /> : "Job no longer exists"}</dd></div>
          <div><dt className="text-slate-500">Resume</dt><dd className="mt-1 font-medium">{application.resumeFileName}</dd></div>
          <div><dt className="text-slate-500">Reference</dt><dd className="mt-1 break-all font-mono text-xs text-slate-600">{application.id}</dd></div>
        </dl>
        <a href={`/applications/${application.id}/resume`} download={application.resumeFileName} className="mt-6 block rounded-lg bg-slate-900 px-4 py-2.5 text-center text-sm font-semibold text-white">Download resume (PDF)</a>
      </aside>
      <div className="space-y-6">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Message from the candidate</h2>{application.message ? <p className="mt-4 whitespace-pre-line leading-7 text-slate-700">{application.message}</p> : <p className="mt-4 text-sm text-slate-500">The candidate did not include a message.</p>}</section>
        <section className="rounded-xl border border-dashed border-cyan-200 bg-cyan-50/40 p-6"><div className="flex items-center justify-between gap-3"><div><p className="text-sm font-semibold text-cyan-700">AI evaluation</p><h2 className="mt-1 text-xl font-bold">Not evaluated yet</h2></div><StatusBadge status={pendingEvaluation} /></div><p className="mt-4 text-sm leading-6 text-slate-600">Resume screening, scoring, and recommendations will be added in a later phase. Until then, review the resume and message directly.</p></section>
      </div>
    </div>
  </>;
}
