import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApplicationForm } from "@/components/application-form";
import { BriefcaseIcon, LocationIcon } from "@/components/icons";
import { getJob, jobs } from "@/data/jobs";

type ApplyPageProps = { params: Promise<{ id: string }> };

export const metadata: Metadata = { title: "Apply | Northstar", description: "Apply for a role at Northstar." };
export function generateStaticParams() { return jobs.map((job) => ({ id: job.id })); }

export default async function ApplyPage({ params }: ApplyPageProps) {
  const job = getJob((await params).id);
  if (!job) notFound();
  return <main className="apply-page"><section className="apply-hero"><div className="container narrow"><Link className="back-link" href={`/jobs/${job.id}`}>← Back to role</Link><span className="eyebrow">Application</span><h1>{job.title}</h1><div className="job-meta"><span><LocationIcon />{job.location} · {job.workplace}</span><span><BriefcaseIcon />{job.type}</span></div></div></section><section className="section form-container"><div className="container narrow"><div className="demo-notice"><strong>Demo application</strong><span>This form uses mock interactions only. Your information is not transmitted or stored.</span></div><ApplicationForm jobTitle={job.title} /></div></section></main>;
}
