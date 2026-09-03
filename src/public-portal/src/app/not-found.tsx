import Link from "next/link";

export default function NotFound() {
  return <main className="not-found"><div><span className="eyebrow">404 · Page not found</span><h1>This path doesn&apos;t lead to an open role.</h1><p>The opportunity may have moved, but there are more paths to explore.</p><Link className="button button-primary" href="/jobs">View open roles</Link></div></main>;
}
