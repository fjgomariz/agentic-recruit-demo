import { AutoRefresh } from "@/components/auto-refresh";
import { CandidatesList } from "@/components/candidates-list";
import { getApplications, getJobs } from "@/data/jobs";
import { isEvaluating } from "@/lib/evaluation";

export default async function CandidatesPage() {
  const [applications, jobs] = await Promise.all([getApplications(), getJobs()]);
  return <>
    {applications.some(isEvaluating) && <AutoRefresh intervalMs={4000} />}
    <div className="mb-8"><p className="text-sm font-medium text-cyan-700">Candidate review</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Candidates</h1><p className="mt-2 text-slate-500">Every application goes through a two-agent assessment: the evaluator scores the resume against the job, and a reviewer on a different model checks that evaluation. The scores are advisory: you approve who advances.</p></div>
    <CandidatesList applications={applications} jobs={jobs} />
  </>;
}
