import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRightIcon, BriefcaseIcon, CheckIcon, ClockIcon, LocationIcon } from "@/components/icons";
import { getJob, jobs } from "@/data/jobs";

type JobPageProps = { params: Promise<{ id: string }> };

export function generateStaticParams() { return jobs.map((job) => ({ id: job.id })); }

export async function generateMetadata({ params }: JobPageProps): Promise<Metadata> {
  const job = getJob((await params).id);
  return { title: job ? `${job.title} | Northstar` : "Role not found | Northstar", description: job?.summary };
}

export default async function JobDetailsPage({ params }: JobPageProps) {
  const job = getJob((await params).id);
  if (!job) notFound();

  return <main>
    <section className="job-hero"><div className="container"><Link className="back-link" href="/jobs">← Back to open roles</Link><div className="job-hero-content"><div><span className="eyebrow">{job.team}</span><h1>{job.title}</h1><p>{job.summary}</p><div className="job-meta hero-meta"><span><LocationIcon />{job.location} · {job.workplace}</span><span><BriefcaseIcon />{job.type}</span><span><ClockIcon />Posted {job.posted}</span></div></div><Link className="button button-primary" href={`/jobs/${job.id}/apply`}>Apply for this role <ArrowRightIcon /></Link></div></div></section>
    <section className="section"><div className="container details-layout"><article className="job-copy"><h2>About the role</h2><p>{job.description}</p><h2>What you&apos;ll do</h2><ul>{job.responsibilities.map((item) => <li key={item}><CheckIcon />{item}</li>)}</ul><h2>What you&apos;ll bring</h2><ul>{job.qualifications.map((item) => <li key={item}><CheckIcon />{item}</li>)}</ul><h2>Nice to have</h2><ul>{job.preferred.map((item) => <li key={item}><CheckIcon />{item}</li>)}</ul></article><aside className="apply-card"><span className="eyebrow">Ready to begin?</span><h2>Make your next move matter.</h2><p>We review every application with care and look forward to learning about you.</p><Link className="button button-primary" href={`/jobs/${job.id}/apply`}>Apply now <ArrowRightIcon /></Link><small>Usually takes 5–10 minutes</small></aside></div></section>
  </main>;
}
