import type { JobApplication } from "@domain";
import Link from "next/link";
import { Score, StatusBadge } from "@/components/ui";
import { evaluationLabel, scoreOf } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

export function ApplicationsTable({ applications }: { applications: JobApplication[] }) {
  if (applications.length === 0) {
    return <p className="p-8 text-center text-sm text-slate-500">No applications yet. They appear here as soon as candidates apply on the careers site.</p>;
  }

  return (
    <div className="overflow-x-auto"><table className="w-full min-w-175 text-left text-sm">
      <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Score</th><th className="px-5 py-3 font-semibold">Candidate</th><th className="px-5 py-3 font-semibold">AI recommendation</th><th className="px-5 py-3 font-semibold">Decision</th><th className="px-5 py-3 font-semibold">Submitted</th><th className="px-5 py-3 font-semibold">Resume</th></tr></thead>
      <tbody className="divide-y divide-slate-100">{applications.map((application) => <tr key={application.id} className="align-top hover:bg-slate-50">
        <td className="px-5 py-4"><Score value={scoreOf(application)} /></td>
        <td className="px-5 py-4"><Link href={`/candidates/${application.id}`} className="font-semibold hover:text-cyan-700 hover:underline">{application.candidateName}</Link><p className="mt-1"><a className="text-cyan-700 hover:underline" href={`mailto:${application.candidateEmail}`}>{application.candidateEmail}</a></p>{application.message && <p className="mt-1 max-w-md whitespace-pre-line text-slate-500">{application.message}</p>}</td>
        <td className="px-5 py-4"><StatusBadge status={evaluationLabel(application)} /></td>
        <td className="px-5 py-4">{application.decision ? <StatusBadge status={application.decision.status} /> : <span className="text-slate-400">—</span>}</td>
        <td className="whitespace-nowrap px-5 py-4 text-slate-600">{formatDateTime(application.submittedAt)}</td>
        <td className="px-5 py-4"><a className="inline-flex items-center gap-2 font-semibold text-cyan-700 hover:underline" href={`/applications/${application.id}/resume`} download={application.resumeFileName}>⬇ {application.resumeFileName}</a></td>
      </tr>)}</tbody>
    </table></div>
  );
}
