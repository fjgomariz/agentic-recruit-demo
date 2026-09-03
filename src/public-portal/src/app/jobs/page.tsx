import type { Metadata } from "next";
import { JobList } from "@/components/job-list";
import { jobs } from "@/data/jobs";

export const metadata: Metadata = { title: "Open roles | Northstar", description: "Explore open roles at Northstar." };

export default function JobsPage() {
  return <main><section className="page-hero"><div className="container narrow"><span className="eyebrow">Join the team</span><h1>Find work that moves you forward.</h1><p>Bring your perspective, curiosity, and ambition. We are building a team where thoughtful people solve meaningful problems together.</p></div></section><section className="section jobs-section"><div className="container"><JobList jobs={jobs} /></div></section></main>;
}
