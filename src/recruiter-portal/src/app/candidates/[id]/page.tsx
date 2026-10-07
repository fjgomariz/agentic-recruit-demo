import Link from "next/link";
import { notFound } from "next/navigation";
import type { ApplicationEvaluation, ApplicationReview, JobApplication, ReviewFinding } from "@domain";
import { AutoRefresh } from "@/components/auto-refresh";
import { ApprovalPanel, EvaluateButton, ReviewButton } from "@/components/candidate-actions";
import { Avatar, Score, StatusBadge } from "@/components/ui";
import { getApplication, getJob } from "@/data/jobs";
import { evaluationLabel, finalRecommendation, isEvaluating, isReviewed, isRunning, isStalled, scoreOf, workflowStage } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

const evaluatorModel = "gpt-5.4-mini";
const reviewerModel = "gpt-5.4";

function duration(step: { startedAt: string; completedAt?: string }): string | undefined {
  if (!step.completedAt) return undefined;
  return `${((new Date(step.completedAt).getTime() - new Date(step.startedAt).getTime()) / 1000).toFixed(1)}s`;
}

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" aria-hidden="true" />;
}

function RunFooter({ step, children }: { step: ApplicationEvaluation | ApplicationReview; children?: React.ReactNode }) {
  const time = duration(step);
  return <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4">
    <p className="text-xs text-slate-500">{step.agentName}{step.agentVersion ? ` v${step.agentVersion}` : ""}{step.model ? ` · ${step.model}` : ""} · {step.completedAt ? formatDateTime(step.completedAt) : ""}{time ? ` · ${time}` : ""}{step.agentExecutionId ? <> · <span className="font-mono">{step.agentExecutionId}</span></> : null}</p>
    {children}
  </div>;
}

type StepState = "done" | "running" | "waiting" | "problem" | "skipped";

function WorkflowStepper({ application }: { application: JobApplication }) {
  const evaluation = application.evaluation;
  const review = application.review;
  const evaluationState: StepState = !evaluation ? "waiting" : isRunning(evaluation) ? "running" : evaluation.status === "Completed" ? "done" : "problem";
  const reviewState: StepState = evaluation?.status !== "Completed" ? (evaluation?.status === "Needs review" ? "skipped" : "waiting") : !review ? "waiting" : isRunning(review) ? "running" : review.status === "Completed" ? "done" : "problem";
  const approvalState: StepState = application.decision ? "done" : workflowStage(application) === "Awaiting approval" ? "running" : "waiting";
  const steps = [
    { title: "1 · Evaluate", who: `Evaluator agent · ${evaluation?.model ?? evaluatorModel}`, state: evaluationState, detail: evaluation?.status === "Completed" ? `${evaluation.overallScore}/100 · ${evaluation.recommendation}` : evaluationLabel(application) },
    { title: "2 · Review", who: `Reviewer agent · ${review?.model ?? reviewerModel}`, state: reviewState, detail: review?.status === "Completed" ? `${review.agreement} · ${review.validatedScore}/100` : reviewState === "skipped" ? "Skipped: manual review needed" : isRunning(review) ? "Reviewing…" : isStalled(review) ? "Did not finish" : review?.status ?? "Waiting" },
    { title: "3 · Approve", who: "Recruiter (human in the loop)", state: approvalState, detail: application.decision ? application.decision.status : approvalState === "running" ? "Your decision is needed" : "Waiting" },
  ];
  const tone: Record<StepState, string> = { done: "border-emerald-200 bg-emerald-50", running: "border-blue-300 bg-blue-50", waiting: "border-slate-200 bg-white", problem: "border-rose-200 bg-rose-50", skipped: "border-amber-200 bg-amber-50" };
  const icon: Record<StepState, React.ReactNode> = { done: <span className="text-emerald-600">✓</span>, running: <Spinner />, waiting: <span className="text-slate-300">○</span>, problem: <span className="text-rose-600">!</span>, skipped: <span className="text-amber-600">–</span> };
  return <ol className="mt-6 grid gap-3 md:grid-cols-3" aria-label="Assessment workflow">{steps.map((step, index) => <li key={step.title} className={`relative rounded-xl border p-4 ${tone[step.state]}`}>
    <div className="flex items-center justify-between gap-2"><p className="font-bold">{step.title}</p><span className="grid h-6 w-6 place-items-center text-sm font-bold">{step.state === "running" && index === 2 ? <span className="h-2.5 w-2.5 rounded-full bg-blue-600" /> : icon[step.state]}</span></div>
    <p className="mt-1 text-xs text-slate-500">{step.who}</p>
    <p className="mt-2 text-sm font-medium text-slate-800">{step.detail}</p>
  </li>)}</ol>;
}

function EvaluationReport({ application }: { application: JobApplication }) {
  const evaluation = application.evaluation;
  const heading = <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700">Step 1 · Evaluator agent (maker)</p>;

  if (!evaluation) {
    return <section className="rounded-xl border border-dashed border-cyan-200 bg-cyan-50/40 p-6">
      {heading}<h2 className="mt-1 text-xl font-bold">Not evaluated yet</h2>
      <p className="mt-3 text-sm leading-6 text-slate-600">The evaluator compares the resume with the job&apos;s requirements; a second agent on a different model then checks its work before you decide.</p>
      <div className="mt-5"><EvaluateButton applicationId={application.id} label="Evaluate with AI" /></div>
    </section>;
  }

  if (isRunning(evaluation)) {
    return <section className="rounded-xl border border-blue-100 bg-blue-50/40 p-6" aria-live="polite">
      {heading}
      <h2 className="mt-1 flex items-center gap-3 text-xl font-bold"><Spinner />Evaluating the resume…</h2>
      <p className="mt-3 text-sm text-slate-600">The {evaluation.agentName} agent is reading the PDF. This page updates automatically.</p>
    </section>;
  }

  if (evaluation.status === "Failed" || isStalled(evaluation)) {
    return <section className="rounded-xl border border-rose-200 bg-rose-50/40 p-6">
      {heading}<h2 className="mt-1 text-xl font-bold">{evaluation.status === "Failed" ? "The evaluation failed" : "The evaluation did not finish"}</h2>
      <p className="mt-3 text-sm text-slate-600">{evaluation.status === "Failed" ? evaluation.errorMessage ?? "The agent did not return a result." : "The run was interrupted (for example by a restart). Run it again or decide manually."}</p>
      <div className="mt-5"><EvaluateButton applicationId={application.id} label="Try again" /></div>
    </section>;
  }

  const findings = application.review?.status === "Completed" ? application.review.inconsistencies.length : 0;
  return <section className={`rounded-xl border bg-white p-6 shadow-sm ${evaluation.status === "Needs review" ? "border-rose-200" : "border-cyan-100"}`}>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>{heading}<h2 className="mt-1 text-xl font-bold">{evaluation.overallScore !== undefined && evaluation.overallScore !== null ? `Initial score: ${evaluation.overallScore}/100` : "Not scored"}</h2></div>
      <StatusBadge status={evaluation.recommendation ?? "Needs manual review"} />
    </div>
    {findings > 0 && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">The reviewer flagged {findings} issue{findings === 1 ? "" : "s"} in this evaluation. See step 2.</p>}
    {evaluation.summary && <p className="mt-4 leading-7 text-slate-700">{evaluation.summary}</p>}
    <div className="mt-6 grid gap-6 md:grid-cols-2">
      <div><h3 className="font-bold text-emerald-700">Strengths</h3>{evaluation.strengths.length ? <ul className="mt-3 space-y-2 text-sm text-slate-600">{evaluation.strengths.map((item) => <li key={item} className="flex gap-2"><span className="text-emerald-600">✓</span>{item}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">None identified.</p>}</div>
      <div><h3 className="font-bold text-amber-700">Considerations</h3>{evaluation.considerations.length ? <ul className="mt-3 space-y-2 text-sm text-slate-600">{evaluation.considerations.map((item) => <li key={item} className="flex gap-2"><span className="text-amber-600">•</span>{item}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">None identified.</p>}</div>
    </div>
    {evaluation.scores.length > 0 && <details className="mt-6 rounded-lg border border-slate-200"><summary className="cursor-pointer p-4 text-sm font-bold">Requirements ({evaluation.scores.length})</summary><div className="divide-y divide-slate-100 border-t border-slate-200">{evaluation.scores.map((score) => <div key={score.id} className="grid gap-2 p-4 md:grid-cols-[1fr_140px]">
      <div><p className="text-sm font-semibold">{score.criterion}</p>{score.rationale && <p className="mt-1 text-sm text-slate-500">{score.rationale}</p>}</div>
      <div className="flex items-center gap-2 md:justify-end" title={`${score.value} of ${score.maximumValue}`}><div className="flex gap-1" aria-hidden="true">{Array.from({ length: score.maximumValue }, (_, index) => <span key={index} className={`h-2 w-5 rounded-full ${index < score.value ? "bg-cyan-600" : "bg-slate-200"}`} />)}</div><span className="text-xs font-semibold text-slate-600">{score.value}/{score.maximumValue}</span></div>
    </div>)}</div></details>}
    <RunFooter step={evaluation}><EvaluateButton applicationId={application.id} label="Re-run assessment" /></RunFooter>
  </section>;
}

const severityStyle: Record<ReviewFinding["severity"], string> = { High: "bg-rose-100 text-rose-800", Medium: "bg-amber-100 text-amber-800", Low: "bg-slate-100 text-slate-700" };
const agreementStyle: Record<string, string> = { Agrees: "bg-emerald-50 text-emerald-700", "Partially agrees": "bg-amber-50 text-amber-700", Disagrees: "bg-rose-50 text-rose-700" };

function ReviewReport({ application }: { application: JobApplication }) {
  const review = application.review;
  const evaluation = application.evaluation;
  const heading = <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">Step 2 · Reviewer agent (checker)</p>;

  if (!evaluation || evaluation.status === "In progress" || evaluation.status === "Failed") {
    return <section className="rounded-xl border border-dashed border-slate-200 bg-white p-6">{heading}<h2 className="mt-1 text-lg font-bold text-slate-500">Waiting for the evaluation</h2><p className="mt-2 text-sm text-slate-500">A second agent on {reviewerModel} will check the evaluation against the resume for unsupported claims, missed evidence, bias, and overconfidence.</p></section>;
  }
  if (evaluation.status === "Needs review") {
    return <section className="rounded-xl border border-dashed border-amber-200 bg-amber-50/40 p-6">{heading}<h2 className="mt-1 text-lg font-bold">Skipped</h2><p className="mt-2 text-sm text-slate-600">The evaluation was routed to manual review, so there is nothing for the reviewer to check.</p></section>;
  }
  if (!review) {
    return <section className="rounded-xl border border-dashed border-violet-200 bg-violet-50/40 p-6">{heading}<h2 className="mt-1 text-xl font-bold">Not reviewed yet</h2><p className="mt-2 text-sm text-slate-600">This evaluation was produced before the reviewer existed. Run the reviewer to validate it.</p><div className="mt-5"><ReviewButton applicationId={application.id} label="Review with AI" /></div></section>;
  }
  if (isRunning(review)) {
    return <section className="rounded-xl border border-violet-200 bg-violet-50/40 p-6" aria-live="polite">{heading}<h2 className="mt-1 flex items-center gap-3 text-xl font-bold"><Spinner />Checking the evaluation…</h2><p className="mt-3 text-sm text-slate-600">The {review.agentName} agent on {reviewerModel} is re-reading the resume and verifying each claim. This usually takes 15–20 seconds.</p></section>;
  }
  if (review.status !== "Completed") {
    const stalled = isStalled(review);
    return <section className="rounded-xl border border-rose-200 bg-rose-50/40 p-6">{heading}<h2 className="mt-1 text-xl font-bold">{stalled ? "The review did not finish" : review.status === "Failed" ? "The review failed" : "Not reviewed automatically"}</h2><p className="mt-2 text-sm text-slate-600">{stalled ? "The run was interrupted (for example by a restart). Run it again or decide on the unreviewed evaluation." : review.errorMessage ?? review.summary ?? "The reviewer did not return a result."}</p><div className="mt-5"><ReviewButton applicationId={application.id} label="Try the review again" /></div></section>;
  }

  const delta = (review.validatedScore ?? 0) - (review.originalScore ?? 0);
  return <section className="rounded-xl border border-violet-200 bg-white p-6 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>{heading}<h2 className="mt-1 text-xl font-bold">Validated score: {review.validatedScore}/100</h2><p className="mt-1 text-sm text-slate-500">Evaluator {review.originalScore}/100 → reviewer {review.validatedScore}/100 <span className={delta === 0 ? "text-slate-500" : delta > 0 ? "text-emerald-700" : "text-rose-700"}>({delta > 0 ? "+" : ""}{delta})</span> · confidence {review.confidence}</p></div>
      <div className="flex flex-wrap gap-2"><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${agreementStyle[review.agreement ?? ""] ?? "bg-slate-100 text-slate-600"}`}>{review.agreement}</span>{review.finalRecommendation && <StatusBadge status={review.finalRecommendation} />}</div>
    </div>
    {review.summary && <p className="mt-4 leading-7 text-slate-700">{review.summary}</p>}
    <div className="mt-6"><h3 className="font-bold">Inconsistencies found</h3>{review.inconsistencies.length === 0 ? <p className="mt-2 text-sm text-emerald-700">✓ No inconsistencies: the evaluation is supported by the resume.</p> : <ul className="mt-3 space-y-3">{review.inconsistencies.map((finding, index) => <li key={index} className="rounded-lg border border-slate-200 p-3"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityStyle[finding.severity]}`}>{finding.severity}</span><span className="text-sm font-semibold">{finding.type}</span></div><p className="mt-2 text-sm text-slate-600">{finding.description}</p></li>)}</ul>}</div>
    {review.comments.length > 0 && <div className="mt-6"><h3 className="font-bold">Review comments</h3><ul className="mt-3 space-y-2 text-sm text-slate-600">{review.comments.map((comment) => <li key={comment} className="flex gap-2"><span className="text-violet-600">›</span>{comment}</li>)}</ul></div>}
    <RunFooter step={review}><ReviewButton applicationId={application.id} label="Re-run review" /></RunFooter>
  </section>;
}

export default async function CandidateDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const application = await getApplication(id);
  if (!application) notFound();
  const job = await getJob(application.jobId);
  const score = scoreOf(application);
  const running = isEvaluating(application);

  return <>
    {running && <AutoRefresh />}
    <Link href="/candidates" className="text-sm font-semibold text-cyan-700">← All candidates</Link>
    <div className="mt-5 flex flex-wrap items-center gap-4">
      {score !== undefined ? <Score value={score} size="lg" /> : <Avatar name={application.candidateName} />}
      <div><h1 className="text-3xl font-bold tracking-tight">{application.candidateName}</h1><p className="mt-1 text-slate-500">Applied for {job ? <Link href={`/jobs/${job.id}`} className="font-medium text-cyan-700 hover:underline">{job.title}</Link> : application.jobId}</p></div>
      <div className="ml-auto flex gap-2">{!running && <StatusBadge status={evaluationLabel(application)} />}{application.decision && <StatusBadge status={application.decision.status} />}</div>
    </div>
    <WorkflowStepper application={application} />
    <div className="mt-7 grid gap-6 lg:grid-cols-[.8fr_1.4fr]">
      <div className="space-y-6">
        <ApprovalPanel applicationId={application.id} decision={application.decision} recommendation={finalRecommendation(application)} score={score} reviewed={isReviewed(application)} aiRunning={running} currentEvaluationId={application.evaluation?.agentExecutionId} currentReviewId={application.review?.agentExecutionId} />
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
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold">Message from the candidate</h2>{application.message ? <p className="mt-4 whitespace-pre-line leading-7 text-slate-700">{application.message}</p> : <p className="mt-4 text-sm text-slate-500">The candidate did not include a message.</p>}</section>
      </div>
      <div className="space-y-6">
        <EvaluationReport application={application} />
        <ReviewReport application={application} />
      </div>
    </div>
  </>;
}
