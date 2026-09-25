"use client";

import Link from "next/link";

export default function JobsError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-rose-200 bg-white p-8 shadow-sm">
      <p className="text-sm font-semibold text-rose-700">Job service unavailable</p>
      <h1 className="mt-2 text-2xl font-bold">The job could not be loaded or saved.</h1>
      <p className="mt-2 text-slate-500">The backend API or Cosmos DB did not complete the request. No changes were lost from the stored job record.</p>
      <div className="mt-6 flex gap-3">
        <button onClick={reset} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white">Try again</button>
        <Link href="/jobs" className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold">All job postings</Link>
      </div>
    </div>
  );
}
