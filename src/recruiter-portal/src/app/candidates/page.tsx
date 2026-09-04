import { CandidatesList } from "@/components/candidates-list";
import { candidateDetails } from "@/data/mock-data";
import { getJobs } from "@/data/jobs";

export default async function CandidatesPage() {
  const jobs = await getJobs();
  return <CandidatesList candidateDetails={candidateDetails} jobs={jobs} />;
}
