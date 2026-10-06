import Link from "next/link";
import { notFound } from "next/navigation";
import type { ApplicationEvaluation, JobApplication } from "@domain";
import { AutoRefresh } from "@/components/auto-refresh";
import { DecisionPanel, EvaluateButton } from "@/components/candidate-actions";
import { Avatar, Score, StatusBadge } from "@/components/ui";
import { getApplication, getJob } from "@/data/jobs";
import { evaluationLabel, isEvaluating, scoreOf } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

function durationLabel(evaluation: ApplicationEvaluation): string | undefined {
  if (!evaluation.completedAt) return undefined;
  return `${((new Date(evaluation.completedAt).getTime() - new Date(evaluation.startedAt).getTime()) / 1000).toFixed(1)}s`;
}

function EvaluationReport({ application }: { application: JobApplication }) {
  const evaluation = application.evaluation;

  if (!evaluation) {
    return <section className="rounded-xl border border-dashed border-cyan-200 bg-cyan-50/40 p-6">
      <p className="text-sm font-semibold text-cyan-700">AI evaluation</p><h2 className="mt-1 text-xl font-bold">Not evaluated yet</h2>
      <p className="mt-3 text-sm leading-6 text-slate-600">The candidate evaluator compares the resume with the job&apos;s requirements and explains the evidence. Your decision stays separate.</p>
      <div className="mt-5"><EvaluateButton applicationId={application.id} label="Evaluate with AI" /></div>
    </section>;
  }

  if (evaluation.status === "In progress") {
    return <section className="rounded-xl border border-blue-100 bg-blue-50/40 p-6" aria-live="polite">
      <AutoRefresh />
      <p className="text-sm font-semibold text-blue-700">AI evaluation</p>
      <h2 className="mt-1 flex items-center gap-3 text-xl font-bold"><span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" aria-hidden="true" />Evaluating the resume…</h2>
      <p className="mt-3 text-sm text-slate-600">The {evaluation.agentName} agent is reading the PDF. This page updates automatically, usually within 20 seconds.</p>
    </section>;
  }

  if (evaluation.status === "Failed") {
    return <section className="rounded-xl border border-rose-200 bg-rose-50/40 p-6">
      <p className="text-sm font-semibold text-rose-700">AI evaluation</p><h2 className="mt-1 text-xl font-bold">The evaluation failed</h2>
      <p className="mt-3 text-sm text-slate-600">{evaluation.errorMessage ?? "The agent did not return a result."}</p>
      <div className="mt-5"><EvaluateButton applicationId={application.id} label="Try again" /></div>
    </section>;
  }

  const duration = durationLabel(evaluation);
  return <section className={`rounded-xl border bg-white p-6 shadow-sm ${evaluation.status === "Needs review" ? "border-rose-200" : "border-cyan-100"}`}>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-sm font-semibold text-cyan-700">AI evaluation · advisory</p><h2 className="mt-1 text-xl font-bold">{scoreOf(application) !== undefined ? `Suitability score: ${scoreOf(application)}/100` : "Not scored"}</h2></div>
      <StatusBadge status={evaluationLabel(application)} />
    </div>
    {evaluation.summary && <p className="mt-4 leading-7 text-slate-700">{evaluation.summary}</p>}
    <div className="mt-6 grid gap-6 md:grid-cols-2">
      <div><h3 className="font-bold text-emerald-700">Strengths</h3>{evaluation.strengths.length ? <ul className="mt-3 space-y-2 text-sm text-slate-600">{evaluation.strengths.map((item) => <li key={item} className="flex gap-2"><span className="text-emerald-600">✓</span>{item}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">None identified.</p>}</div>
      <div><h3 className="font-bold text-amber-700">Considerations</h3>{evaluation.considerations.length ? <ul className="mt-3 space-y-2 text-sm text-slate-600">{evaluation.considerations.map((item) => <li key={item} className="flex gap-2"><span className="text-amber-600">•</span>{item}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">None identified.</p>}</div>
    </div>
    {evaluation.scores.length > 0 && <div className="mt-7"><h3 className="font-bold">Requirements</h3><div className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">{evaluation.scores.map((score) => <div key={score.id} className="grid gap-2 p-4 md:grid-cols-[1fr_140px]">
      <div><p className="text-sm font-semibold">{score.criterion}</p>{score.rationale && <p className="mt-1 text-sm text-slate-500">{score.rationale}</p>}</div>
      <div className="flex items-center gap-2 md:justify-end" title={`${score.value} of ${score.maximumValue}`}><div className="flex gap-1" aria-hidden="true">{Array.from({ length: score.maximumValue }, (_, index) => <span key={index} className={`h-2 w-5 rounded-full ${index < score.value ? "bg-cyan-600" : "bg-slate-200"}`} />)}</div><span className="text-xs font-semibold text-slate-600">{score.value}/{score.maximumValue}</span></div>
    </div>)}</div></div>}
    <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4">
      <p className="text-xs text-slate-500">{evaluation.agentName}{evaluation.agentVersion ? ` v${evaluation.agentVersion}` : ""} · {evaluation.completedAt ? formatDateTime(evaluation.completedAt) : ""}{duration ? ` · ${duration}` : ""}{evaluation.agentExecutionId ? <> · <span className="font-mono">{evaluation.agentExecutionId}</span></> : null}</p>
      <EvaluateButton applicationId={application.id} label="Re-evaluate" />
    </div>
  </section>;
}

export default async function CandidateDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const application = await getApplication(id);
  if (!application) notFound();
  const job = await getJob(application.jobId);
  const score = scoreOf(application);

  return <>
    <Link href="/candidates" className="text-sm font-semibold text-cyan-700">← All candidates</Link>
    <div className="mt-5 flex flex-wrap items-center gap-4">
      {score !== undefined ? <Score value={score} size="lg" /> : <Avatar name={application.candidateName} />}
      <div><h1 className="text-3xl font-bold tracking-tight">{application.candidateName}</h1><p className="mt-1 text-slate-500">Applied for {job ? <Link href={`/jobs/${job.id}`} className="font-medium text-cyan-700 hover:underline">{job.title}</Link> : application.jobId}</p></div>
      <div className="ml-auto flex gap-2">{!isEvaluating(application) && <StatusBadge status={evaluationLabel(application)} />}{application.decision && <StatusBadge status={application.decision.status} />}</div>
    </div>
    <div className="mt-7 grid gap-6 lg:grid-cols-[.8fr_1.4fr]">
      <div className="space-y-6">
        <aside className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-bold">Application</h2>
          <dl className="mt-5 space-y-4 text-sm">
            <div><dt className="text-slate-500">Email</dt><dd className="mt-1 font-medium"><a className="text-cyan-700 hover:underline" href={`mailto:${application.candidateEmail}`}>{application.candidateEmail}</a></dd></div>
            <div><dt className="text-slate-500">Submitted</dt><dd className="mt-1 font-medium">{formatDateTime(application.submittedAt)}</dd></div>
            <div><dt className="text-slate-500">Job status</dt><dd className="mt-1">{job ? <StatusBadge status={job.status} /> : "Job no longer exists"}</dd></div>
            <div><dt className="text-slate-500">Resume</dt><dd className="mt-1 font-medium">{application.resumeFileName}</dd></div>
            <div><dt className="text-slate-500">Reference</dt><dd className="mt-1 break-all font-mono text-xs text-slate-600">{application.id}</dd></div>
          </dl>
          <a href={`/applications/${application.id}/resume`} download={application.resumeFileName} className="mt-6 block rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-center text-sm font-semibold">Download resume (PDF)</a>
        </aside>
        <DecisionPanel applicationId={application.id} decision={application.decision} recommendation={application.evaluation?.recommendation} />
      </div>
      <div className="space-y-6">
        <EvaluationReport application={application} />
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Message from the candidate</h2>{application.message ? <p className="mt-4 whitespace-pre-line leading-7 text-slate-700">{application.message}</p> : <p className="mt-4 text-sm text-slate-500">The candidate did not include a message.</p>}</section>
      </div>
    </div>
  </>;
}
