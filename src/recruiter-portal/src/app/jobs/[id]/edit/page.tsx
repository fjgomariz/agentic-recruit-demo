import Link from "next/link";
import { notFound } from "next/navigation";
import { JobForm } from "@/components/job-form";
import { StatusBadge } from "@/components/ui";
import { getJob } from "@/data/jobs";

export default async function EditJobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) notFound();

  return <>
    <Link href={`/jobs/${job.id}`} className="text-sm font-semibold text-cyan-700">← Back to job</Link>
    <div className="mb-7 mt-5"><p className="text-sm font-medium text-cyan-700">Job management</p><div className="mt-1 flex items-center gap-3"><h1 className="text-3xl font-bold tracking-tight">Edit job</h1><StatusBadge status={job.status} /></div><p className="mt-2 text-slate-500">Changes are saved to the job record without changing its lifecycle state.</p></div>
    <JobForm job={job} />
  </>;
}
