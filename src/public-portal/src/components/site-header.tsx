import Link from "next/link";
import { SparkIcon } from "@/components/icons";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="container nav-wrap">
        <Link className="brand" href="/" aria-label="Northstar careers home">
          <span className="brand-mark"><SparkIcon width={18} height={18} /></span>
          <span>Northstar</span>
        </Link>
        <nav aria-label="Main navigation">
          <Link href="/jobs">Open roles</Link>
          <Link href="/#culture">Life at Northstar</Link>
          <Link className="nav-cta" href="/jobs">Find your role</Link>
        </nav>
      </div>
    </header>
  );
}
