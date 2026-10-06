import Link from "next/link";
import { Score, StatusBadge } from "@/components/ui";
import { getApplications, getJobs } from "@/data/jobs";
import { awaitsDecision, byBestMatch, evaluationLabel, scoreOf } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

const latestApplicationsShown = 5;
const weekMs = 7 * 24 * 60 * 60 * 1000;

function greeting(now: Date) {
  const hour = Number(new Intl.DateTimeFormat("en-GB", { hour: "numeric", hourCycle: "h23", timeZone: "Europe/Madrid" }).format(now));
  return hour < 12 ? "Good morning" : hour < 19 ? "Good afternoon" : "Good evening";
}

export default async function Dashboard() {
  // Applications are secondary here: the dashboard still renders if they cannot be loaded.
  const [jobs, applications] = await Promise.all([getJobs(), getApplications().catch(() => null)]);
  const now = new Date();
  const publishedJobs = jobs.filter((job) => job.status === "Published");
  const pendingApproval = jobs.filter((job) => job.status === "Pending Approval").length;
  const drafts = jobs.filter((job) => job.status === "Draft").length;
  const jobTitles = new Map(jobs.map((job) => [job.id, job.title]));
  const applicationsPerJob = new Map<string, number>();
  for (const application of applications ?? []) applicationsPerJob.set(application.jobId, (applicationsPerJob.get(application.jobId) ?? 0) + 1);
  const lastWeek = applications?.filter((application) => now.getTime() - new Date(application.submittedAt).getTime() < weekMs).length ?? 0;
  const toDecide = (applications ?? []).filter(awaitsDecision).sort(byBestMatch);
  const notEvaluated = applications?.filter((application) => !application.evaluation || application.evaluation.status === "In progress" || application.evaluation.status === "Failed").length ?? 0;
  const advanced = applications?.filter((application) => application.decision?.status === "Advanced").length ?? 0;
  const unavailable = "—";

  const metrics = [
    ["Open positions", String(publishedJobs.length), `${pendingApproval} awaiting approval · ${drafts} ${drafts === 1 ? "draft" : "drafts"}`],
    ["Applications received", applications ? String(applications.length) : unavailable, applications ? `${lastWeek} in the last 7 days` : "Applications unavailable"],
    ["Awaiting your decision", applications ? String(toDecide.length) : unavailable, applications ? `${notEvaluated} not evaluated yet` : "Applications unavailable"],
    ["Candidates advanced", applications ? String(advanced) : unavailable, "Decided by recruiters, not by AI"],
  ];

  return <>
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-medium text-cyan-700">{new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "Europe/Madrid" }).format(now)}</p><h1 className="mt-1 text-3xl font-bold tracking-tight">{greeting(now)}, Jordan.</h1><p className="mt-2 text-slate-500">Here&apos;s what needs your attention across recruiting.</p></div><Link href="/jobs/new" className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">+ Create job</Link></div>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, detail]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p><p className="mt-2 text-xs font-medium text-slate-500">{detail}</p></div>)}</section>
    <section className="mt-7 grid gap-7 xl:grid-cols-[1.2fr_1fr]">
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm"><div className="flex items-center justify-between border-b border-slate-100 p-5"><div><h2 className="font-bold">Open positions</h2><p className="mt-1 text-sm text-slate-500">Published roles and applications received</p></div><Link href="/jobs" className="text-sm font-semibold text-cyan-700">View all</Link></div><div className="divide-y divide-slate-100">{publishedJobs.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No published jobs yet.</p>}{publishedJobs.map((job) => { const count = applications ? `${applicationsPerJob.get(job.id) ?? 0} ${(applicationsPerJob.get(job.id) ?? 0) === 1 ? "application" : "applications"}` : "—"; return <Link href={`/jobs/${job.id}`} key={job.id} className="flex items-center justify-between gap-4 p-5 hover:bg-slate-50"><div><p className="font-semibold">{job.title}</p><p className="mt-1 text-sm text-slate-500">{job.department} · {job.location.displayName}</p></div><div className="flex items-center gap-4"><span className="whitespace-nowrap text-sm text-slate-500">{count}</span><StatusBadge status={job.status} /></div></Link>; })}</div></div>
      <div className="h-fit rounded-xl border border-slate-200 bg-white shadow-sm"><div className="flex items-center justify-between border-b border-slate-100 p-5"><div><h2 className="font-bold">Candidates awaiting your decision</h2><p className="mt-1 text-sm text-slate-500">Evaluated by AI, best match first</p></div><Link href="/candidates" className="text-sm font-semibold text-cyan-700">View all</Link></div>
        {applications === null && <p className="p-8 text-center text-sm text-rose-700">Applications could not be loaded right now. Try again shortly.</p>}
        {applications !== null && toDecide.length === 0 && <p className="p-8 text-center text-sm text-slate-500">{applications.length === 0 ? "No applications yet." : "You are up to date: no evaluated candidates are waiting for a decision."}</p>}
        <div className="divide-y divide-slate-100">{toDecide.slice(0, latestApplicationsShown).map((application) => <Link key={application.id} href={`/candidates/${application.id}`} className="flex items-center gap-3 p-5 hover:bg-slate-50"><Score value={scoreOf(application)} /><div className="min-w-0 flex-1"><p className="truncate font-semibold">{application.candidateName}</p><p className="mt-1 truncate text-sm text-slate-500">{jobTitles.get(application.jobId) ?? application.jobId} · {formatDateTime(application.submittedAt)}</p></div><StatusBadge status={evaluationLabel(application)} /></Link>)}</div>
      </div>
    </section>
  </>;
}
