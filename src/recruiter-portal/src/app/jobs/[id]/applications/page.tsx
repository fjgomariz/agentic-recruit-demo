import Link from "next/link";
import { notFound } from "next/navigation";
import { ApplicationsTable } from "@/components/applications-table";
import { StatusBadge } from "@/components/ui";
import { getJob, getJobApplications } from "@/data/jobs";

export default async function JobApplicationsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [job, applications] = await Promise.all([getJob(id), getJobApplications(id)]);
  if (!job) notFound();

  return <>
    <Link href={`/jobs/${job.id}`} className="text-sm font-semibold text-cyan-700">← Back to job</Link>
    <div className="mb-7 mt-5"><p className="text-sm font-medium text-cyan-700">Applications</p><div className="mt-1 flex flex-wrap items-center gap-3"><h1 className="text-3xl font-bold tracking-tight">{job.title}</h1><StatusBadge status={job.status} /></div><p className="mt-2 text-slate-500">{applications.length} {applications.length === 1 ? "candidate has" : "candidates have"} applied through the careers site.</p></div>
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><ApplicationsTable applications={applications} /></div>
  </>;
}
