import Link from "next/link";
import { notFound } from "next/navigation";
import { changeJobStatus } from "@/app/jobs/actions";
import { ApplicationsTable } from "@/components/applications-table";
import { getJob, getJobApplications } from "@/data/jobs";
import { StatusBadge } from "@/components/ui";

const secondaryButton = "block w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-center text-sm font-semibold";
const primaryButton = "block w-full rounded-lg bg-slate-900 px-4 py-2.5 text-center text-sm font-semibold text-white";
const recentApplicationsShown = 5;

export default async function JobDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Applications are secondary here: the job page still renders if they cannot be loaded.
  const [job, applications] = await Promise.all([getJob(id), getJobApplications(id).catch(() => null)]);
  if (!job) notFound();

  return <>
    <Link href="/jobs" className="text-sm font-semibold text-cyan-700">← All job postings</Link>
    <div className="mt-5 rounded-xl bg-slate-950 p-7 text-white"><StatusBadge status={job.status} /><h1 className="mt-4 text-3xl font-bold">{job.title}</h1><p className="mt-2 text-slate-300">{job.department} · {job.location.displayName} · Hiring manager: {job.hiringManager}</p></div>
    <div className="mt-7 grid gap-7 lg:grid-cols-[1.5fr_.8fr]">
      <article className="rounded-xl border border-slate-200 bg-white p-7 shadow-sm"><p className="text-sm font-semibold text-cyan-700">{job.authoringExecutionId ? "AI-assisted job description" : "Job description"}</p><p className="mt-2 font-medium text-slate-900">{job.summary}</p><p className="mt-4 whitespace-pre-line leading-7 text-slate-700">{job.description}</p><h2 className="mt-8 text-lg font-bold">Responsibilities</h2><ul className="mt-4 space-y-3">{job.responsibilities.map((item) => <li className="flex gap-3 text-slate-700" key={item}><span className="font-bold text-cyan-600">•</span>{item}</li>)}</ul><h2 className="mt-8 text-lg font-bold">Key qualifications</h2><ul className="mt-4 space-y-3">{job.qualifications.map((requirement) => <li className="flex gap-3 text-slate-700" key={requirement}><span className="font-bold text-cyan-600">✓</span>{requirement}</li>)}</ul>{job.preferredQualifications.length > 0 && <><h2 className="mt-8 text-lg font-bold">Preferred qualifications</h2><ul className="mt-4 space-y-3">{job.preferredQualifications.map((item) => <li className="flex gap-3 text-slate-700" key={item}><span className="font-bold text-slate-400">+</span>{item}</li>)}</ul></>}</article>
      <aside className="h-fit rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Role activity</h2><dl className="mt-5 space-y-4 text-sm"><div><dt className="text-slate-500">Created</dt><dd className="mt-1 font-medium">{new Date(job.createdAt).toLocaleDateString()}</dd></div>{job.publishedAt && <div><dt className="text-slate-500">Published</dt><dd className="mt-1 font-medium">{new Date(job.publishedAt).toLocaleDateString()}</dd></div>}<div><dt className="text-slate-500">Applications</dt><dd className="mt-1 font-medium">{applications ? applications.length : job.applicantCount}</dd></div><div><dt className="text-slate-500">Experience level</dt><dd className="mt-1 font-medium">{job.experienceLevel} · {job.employmentType}</dd></div></dl>
        <div className="mt-6 space-y-3">
          {job.status === "Pending Approval" && <Link href={`/jobs/${job.id}/approval`} className={primaryButton}>Review for approval</Link>}
          {job.status === "Draft" && <form action={changeJobStatus.bind(null, job.id, "Pending Approval")}><button className={primaryButton}>Submit for approval</button></form>}
          {job.status === "Published" && <form action={changeJobStatus.bind(null, job.id, "Closed")}><button className={secondaryButton}>Close job</button></form>}
          {job.status === "Closed" && <form action={changeJobStatus.bind(null, job.id, "Published")}><button className={secondaryButton}>Reopen job</button></form>}
          <Link href={`/jobs/${job.id}/applications`} className={secondaryButton}>View applications</Link>
          <Link href={`/jobs/${job.id}/edit`} className={secondaryButton}>Edit job</Link>
        </div>
      </aside>
    </div>
    <section className="mt-7 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 p-5"><div><h2 className="font-bold">Recent applications</h2><p className="mt-1 text-sm text-slate-500">Candidates who applied on the careers site</p></div><Link href={`/jobs/${job.id}/applications`} className="text-sm font-semibold text-cyan-700">View all</Link></div>
      {applications ? <ApplicationsTable applications={applications.slice(0, recentApplicationsShown)} /> : <p className="p-8 text-center text-sm text-rose-700">Applications could not be loaded right now. Try again shortly.</p>}
    </section>
  </>;
}
