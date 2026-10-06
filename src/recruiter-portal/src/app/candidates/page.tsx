import { CandidatesList } from "@/components/candidates-list";
import { getApplications, getJobs } from "@/data/jobs";

export default async function CandidatesPage() {
  const [applications, jobs] = await Promise.all([getApplications(), getJobs()]);
  return <>
    <div className="mb-8"><p className="text-sm font-medium text-cyan-700">Candidate review</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Candidates</h1><p className="mt-2 text-slate-500">Everyone who applied through the careers site, newest first. AI evaluation will be added in a later phase.</p></div>
    <CandidatesList applications={applications} jobs={jobs} />
  </>;
}
