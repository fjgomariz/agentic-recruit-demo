import Link from "next/link";
import type { Job } from "@domain";
import { getPublishedLabel } from "@/data/jobs";
import { ArrowRightIcon, BriefcaseIcon, ClockIcon, LocationIcon } from "@/components/icons";

export function JobCard({ job }: { job: Job }) {
  return (
    <article className="job-card">
      <div className="job-card-top">
        <span className="eyebrow">{job.department}</span>
        <span className="posted"><ClockIcon width={16} height={16} />{getPublishedLabel(job)}</span>
      </div>
      <h3><Link href={`/jobs/${job.id}`}>{job.title}</Link></h3>
      <p>{job.summary}</p>
      <div className="job-meta">
        <span><LocationIcon width={17} height={17} />{job.location.displayName} · {job.location.workplaceType}</span>
        <span><BriefcaseIcon width={17} height={17} />{job.employmentType}</span>
      </div>
      <Link className="text-link" href={`/jobs/${job.id}`}>View role <ArrowRightIcon width={17} height={17} /></Link>
    </article>
  );
}
