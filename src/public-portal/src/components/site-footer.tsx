import Link from "next/link";
import { SparkIcon } from "@/components/icons";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div>
          <Link className="brand footer-brand" href="/"><span className="brand-mark"><SparkIcon width={18} height={18} /></span><span>Northstar</span></Link>
          <p>Building technology that helps people do their most meaningful work.</p>
        </div>
        <div className="footer-links"><strong>Careers</strong><Link href="/jobs">Open roles</Link><Link href="/#culture">Our culture</Link></div>
        <div className="footer-links"><strong>Connect</strong><a href="mailto:careers@northstar.example">Contact careers</a><a href="#">LinkedIn</a></div>
      </div>
      <div className="container footer-bottom"><span>© 2026 Northstar. Demo experience.</span><span>Equal opportunity employer</span></div>
    </footer>
  );
}
