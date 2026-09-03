"use client";

import { useMemo, useState } from "react";
import { JobCard } from "@/components/job-card";
import { SearchIcon } from "@/components/icons";
import type { Job } from "@domain";

export function JobList({ jobs }: { jobs: Job[] }) {
  const [query, setQuery] = useState("");
  const [team, setTeam] = useState("All teams");
  const [workplace, setWorkplace] = useState("All workplaces");

  const teams = ["All teams", ...Array.from(new Set(jobs.map((job) => job.department)))];
  const workplaces = ["All workplaces", ...Array.from(new Set(jobs.map((job) => job.location.workplaceType)))];
  const filteredJobs = useMemo(() => jobs.filter((job) => {
    const searchTarget = `${job.title} ${job.department} ${job.location.displayName} ${job.summary}`.toLowerCase();
    return searchTarget.includes(query.toLowerCase()) && (team === "All teams" || job.department === team) && (workplace === "All workplaces" || job.location.workplaceType === workplace);
  }), [jobs, query, team, workplace]);

  return (
    <>
      <div className="filters">
        <label className="search-field"><span className="sr-only">Search roles</span><SearchIcon /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by role, team, or location" /></label>
        <label><span className="sr-only">Filter by team</span><select value={team} onChange={(event) => setTeam(event.target.value)}>{teams.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label><span className="sr-only">Filter by workplace</span><select value={workplace} onChange={(event) => setWorkplace(event.target.value)}>{workplaces.map((item) => <option key={item}>{item}</option>)}</select></label>
      </div>
      <div className="results-heading"><strong>{filteredJobs.length} open {filteredJobs.length === 1 ? "role" : "roles"}</strong><span>Opportunities to do meaningful work</span></div>
      {filteredJobs.length > 0 ? <div className="jobs-grid">{filteredJobs.map((job) => <JobCard key={job.id} job={job} />)}</div> : <div className="empty-state"><SearchIcon width={30} height={30} /><h2>No matching roles</h2><p>Try broadening your search or changing a filter.</p><button className="button button-secondary" onClick={() => { setQuery(""); setTeam("All teams"); setWorkplace("All workplaces"); }}>Clear filters</button></div>}
    </>
  );
}
