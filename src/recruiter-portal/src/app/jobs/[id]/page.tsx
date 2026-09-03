import Link from "next/link";
import { notFound } from "next/navigation";
import { jobs } from "@/data/mock-data";
import { StatusBadge } from "@/components/ui";

export function generateStaticParams() { return jobs.map(({ id }) => ({ id })); }
export default async function JobDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = jobs.find((item) => item.id === id); if (!job) notFound();
  return <><Link href="/jobs" className="text-sm font-semibold text-cyan-700">← All job postings</Link><div className="mt-5 rounded-xl bg-slate-950 p-7 text-white"><StatusBadge status={job.status} /><h1 className="mt-4 text-3xl font-bold">{job.title}</h1><p className="mt-2 text-slate-300">{job.department} · {job.location} · Hiring manager: {job.hiringManager}</p></div><div className="mt-7 grid gap-7 lg:grid-cols-[1.5fr_.8fr]"><article className="rounded-xl border border-slate-200 bg-white p-7 shadow-sm"><p className="text-sm font-semibold text-cyan-700">AI-generated job description</p><p className="mt-4 leading-7 text-slate-700">{job.aiDescription}</p><h2 className="mt-8 text-lg font-bold">Key requirements</h2><ul className="mt-4 space-y-3">{job.requirements.map((requirement) => <li className="flex gap-3 text-slate-700" key={requirement}><span className="font-bold text-cyan-600">✓</span>{requirement}</li>)}</ul></article><aside className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Role activity</h2><dl className="mt-5 space-y-4 text-sm"><div><dt className="text-slate-500">Created</dt><dd className="mt-1 font-medium">{job.createdAt}</dd></div><div><dt className="text-slate-500">Applicants</dt><dd className="mt-1 font-medium">{job.applicants}</dd></div></dl>{job.status === "Pending Approval" && <Link href={`/jobs/${job.id}/approval`} className="mt-6 block rounded-lg bg-slate-900 px-4 py-2.5 text-center text-sm font-semibold text-white">Review for approval</Link>}</aside></div></>;
}
