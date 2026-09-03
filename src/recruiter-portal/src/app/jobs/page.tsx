import Link from "next/link";
import { jobs } from "@/data/mock-data";
import { StatusBadge } from "@/components/ui";

export default function JobsPage() {
  return (
    <>
      <div className="mb-8 flex items-end justify-between">
        <div><p className="text-sm font-medium text-cyan-700">Job management</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Job postings</h1><p className="mt-2 text-slate-500">Create, refine, and approve positions before publication.</p></div>
        <button className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white">+ Create job</button>
      </div>
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><div className="overflow-x-auto"><table className="w-full min-w-175 text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Role</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 font-semibold">Applicants</th><th className="px-5 py-3 font-semibold">Hiring manager</th><th className="px-5 py-3 font-semibold">Created</th><th /></tr></thead>
        <tbody className="divide-y divide-slate-100">{jobs.map((job) => <tr key={job.id} className="hover:bg-slate-50">
          <td className="px-5 py-4"><p className="font-semibold">{job.title}</p><p className="mt-1 text-slate-500">{job.department} · {job.location.displayName}</p></td>
          <td className="px-5 py-4"><StatusBadge status={job.status} /></td><td className="px-5 py-4 text-slate-600">{job.applicantCount}</td><td className="px-5 py-4 text-slate-600">{job.hiringManager}</td><td className="px-5 py-4 text-slate-500">{new Date(job.createdAt).toLocaleDateString()}</td>
          <td className="px-5 py-4"><Link className="font-semibold text-cyan-700" href={job.status === "Pending Approval" ? `/jobs/${job.id}/approval` : `/jobs/${job.id}`}>{job.status === "Pending Approval" ? "Review" : "View"}</Link></td>
        </tr>)}</tbody>
      </table></div></div>
    </>
  );
}
