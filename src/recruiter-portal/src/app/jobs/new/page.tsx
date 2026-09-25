import Link from "next/link";
import { JobForm } from "@/components/job-form";

export default function NewJobPage() {
  return <>
    <Link href="/jobs" className="text-sm font-semibold text-cyan-700">← All job postings</Link>
    <div className="mb-7 mt-5"><p className="text-sm font-medium text-cyan-700">Job management</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Create job</h1><p className="mt-2 text-slate-500">Save a draft or submit the role for human approval before publication.</p></div>
    <JobForm />
  </>;
}
