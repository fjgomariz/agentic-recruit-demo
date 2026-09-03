import Link from "next/link";
import { ArrowRightIcon, GrowthIcon, PeopleIcon, SparkIcon } from "@/components/icons";
import { JobCard } from "@/components/job-card";
import { jobs } from "@/data/jobs";

export default function Home() {
  return (
    <main>
      <section className="home-hero">
        <div className="hero-orb hero-orb-one" /><div className="hero-orb hero-orb-two" />
        <div className="container hero-grid">
          <div className="hero-copy"><span className="eyebrow light"><SparkIcon width={16} height={16} /> Careers at Northstar</span><h1>Build what&apos;s next.<br /><em>Grow into who&apos;s next.</em></h1><p>Join thoughtful, ambitious people using technology to make work more human—and make an impact that reaches far beyond your role.</p><div className="hero-actions"><Link className="button button-light" href="/jobs">Explore open roles <ArrowRightIcon /></Link><Link className="button button-ghost" href="#culture">Discover our culture</Link></div></div>
          <div className="hero-art" aria-hidden="true"><div className="art-panel"><div className="art-top"><span /><span /><span /></div><div className="art-content"><div className="art-chip">Create with purpose</div><div className="art-line long" /><div className="art-line" /><div className="art-cards"><div><PeopleIcon /><b>Belong</b></div><div><GrowthIcon /><b>Grow</b></div><div><SparkIcon /><b>Impact</b></div></div></div></div><div className="floating-note">Great work starts<br />with great people <span>↗</span></div></div>
        </div>
      </section>
      <section className="proof-strip"><div className="container"><p>One team, many perspectives</p><div><strong>18</strong><span>countries represented</span></div><div><strong>42%</strong><span>women in leadership</span></div><div><strong>4.8/5</strong><span>employee experience</span></div></div></section>
      <section className="section featured"><div className="container"><div className="section-heading"><div><span className="eyebrow">Featured opportunities</span><h2>Find your place on the team.</h2></div><Link className="text-link" href="/jobs">View all open roles <ArrowRightIcon /></Link></div><div className="jobs-grid">{jobs.filter((job) => job.featured).map((job) => <JobCard key={job.id} job={job} />)}</div></div></section>
      <section className="section culture" id="culture"><div className="container culture-grid"><div className="culture-visual"><div className="culture-card culture-card-one"><span>Curiosity</span><strong>Ask better questions.</strong></div><div className="culture-card culture-card-two"><span>Craft</span><strong>Care about the details.</strong></div><div className="culture-center"><SparkIcon width={38} height={38} /></div></div><div className="culture-copy"><span className="eyebrow">How we work</span><h2>Different by design.<br />United by purpose.</h2><p>We believe exceptional teams are built when people feel trusted to bring their full perspective. Here, kindness and high standards belong in the same room.</p><div className="value-list"><div><span>01</span><p><strong>Be boldly curious</strong>Question assumptions and keep learning.</p></div><div><span>02</span><p><strong>Build with care</strong>Make choices that earn lasting trust.</p></div><div><span>03</span><p><strong>Win together</strong>Share context, credit, and momentum.</p></div></div></div></div></section>
      <section className="cta-section"><div className="container"><span className="eyebrow light">Your next chapter</span><h2>Do the work you&apos;ll be proud to talk about.</h2><p>There is a place here for your perspective and ambition.</p><Link className="button button-light" href="/jobs">See where you fit <ArrowRightIcon /></Link></div></section>
    </main>
  );
}
