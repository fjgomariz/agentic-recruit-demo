import Link from "next/link";
import { notFound } from "next/navigation";
import { approvalWorkflows, jobs } from "@/data/mock-data";
import { StatusBadge } from "@/components/ui";

export function generateStaticParams() { return jobs.map(({ id }) => ({ id })); }

export default async function ApprovalPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = jobs.find((item) => item.id === id);
  if (!job) notFound();
  const approval = approvalWorkflows.find((item) => item.targetType === "Job" && item.targetId === job.id);

  return <>
    <Link href={`/jobs/${job.id}`} className="text-sm font-semibold text-cyan-700">← Back to job</Link>
    <div className="mt-5 max-w-4xl"><p className="text-sm font-medium text-cyan-700">Human approval required</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Approve job posting</h1><p className="mt-2 text-slate-500">Review recruiter inputs and AI-assisted content before publication.</p></div>
    <div className="mt-7 grid gap-6 lg:grid-cols-2">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Recruiter-provided inputs</h2><dl className="mt-5 space-y-5 text-sm"><div><dt className="text-slate-500">Role title</dt><dd className="mt-1 font-semibold">{job.title}</dd></div><div><dt className="text-slate-500">Department and location</dt><dd className="mt-1 font-semibold">{job.department} · {job.location.displayName}</dd></div><div><dt className="text-slate-500">Hiring manager</dt><dd className="mt-1 font-semibold">{job.hiringManager}</dd></div><div><dt className="text-slate-500">Must-have criteria</dt><dd className="mt-2 space-y-1">{job.qualifications.map((item) => <div key={item}>• {item}</div>)}</dd></div></dl></section>
      <section className="rounded-xl border border-cyan-100 bg-cyan-50/40 p-6 shadow-sm"><div className="flex items-center justify-between gap-3"><h2 className="font-bold">AI-assisted description</h2>{approval && <StatusBadge status={approval.status} />}</div><p className="mt-5 leading-7 text-slate-700">{job.description}</p><p className="mt-6 border-t border-cyan-100 pt-4 text-xs text-slate-500">Execution {job.authoringExecutionId ?? "not recorded"} · Human decision remains required</p></section>
    </div>
    <div className="mt-7 flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-6"><button className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold">Edit before approval</button><button className="rounded-lg border border-rose-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-700">Reject</button><button className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white">Approve and publish</button></div>
  </>;
}
