"use client";

import { useActionState, useState, useTransition } from "react";
import type { ApplicationDecision } from "@domain";
import { recordDecision, reopenDecision, startEvaluation, startReview, type CandidateActionState } from "@/app/candidates/actions";
import { StatusBadge } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

const fieldClass = "mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-cyan-600 focus:outline-none focus:ring-2 focus:ring-cyan-100";

function AgentButton({ label, run, variant = "primary" }: { label: string; run: () => Promise<CandidateActionState>; variant?: "primary" | "secondary" }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string>();
  const style = variant === "primary" ? "bg-cyan-700 text-white hover:bg-cyan-800" : "border border-cyan-200 bg-white text-cyan-800 hover:bg-cyan-50";
  return <div>
    <button type="button" disabled={pending} onClick={() => startTransition(async () => setError((await run()).error))} className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:opacity-60 ${style}`}>
      <span aria-hidden="true">✦</span>{pending ? "Starting…" : label}
    </button>
    {error && <p role="alert" className="mt-2 text-sm text-rose-700">{error}</p>}
  </div>;
}

/** Runs the whole workflow again: evaluator, then reviewer. */
export function EvaluateButton({ applicationId, label }: { applicationId: string; label: string }) {
  return <AgentButton label={label} run={() => startEvaluation(applicationId)} />;
}

/** Runs only the reviewer agent on the current evaluation. */
export function ReviewButton({ applicationId, label }: { applicationId: string; label: string }) {
  return <AgentButton label={label} run={() => startReview(applicationId)} variant="secondary" />;
}

interface ApprovalProps {
  applicationId: string;
  decision?: ApplicationDecision | null;
  /** Final AI recommendation (reviewer's when available). */
  recommendation?: string;
  score?: number;
  reviewed: boolean;
  aiRunning: boolean;
  /** Execution IDs of the advice currently shown, to detect decisions made on older advice. */
  currentEvaluationId?: string;
  currentReviewId?: string;
}

/** Human approval: the recruiter reviews the AI advice, decides, and gives feedback to improve the agents. */
export function ApprovalPanel({ applicationId, decision, recommendation, score, reviewed, aiRunning, currentEvaluationId, currentReviewId }: ApprovalProps) {
  const requiresRating = Boolean(recommendation);
  const [state, formAction, pending] = useActionState<CandidateActionState, FormData>(recordDecision.bind(null, applicationId, requiresRating), {});
  const [reopening, startReopen] = useTransition();
  const [reopenError, setReopenError] = useState<string>();
  // Controlled so typed text survives the automatic form reset when the server action returns an error.
  const [agentFeedback, setAgentFeedback] = useState("");
  const [comment, setComment] = useState("");
  const [aiRating, setAiRating] = useState("");

  if (decision) {
    const stale = (decision.evaluationExecutionId ?? undefined) !== currentEvaluationId || (decision.reviewExecutionId ?? undefined) !== currentReviewId;
    return <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Step 3 · Recruiter approval</p><h2 className="mt-1 font-bold">Final decision</h2></div><StatusBadge status={decision.status} /></div>
      <p className="mt-3 text-sm text-slate-600">{decision.decidedBy} · {formatDateTime(decision.decidedAt)}</p>
      {decision.aiRecommendation && <p className="mt-3 text-sm text-slate-700">AI advice at decision time: <strong>{decision.aiRecommendation}</strong>{decision.aiScore !== null && decision.aiScore !== undefined ? ` (${decision.aiScore}/100)` : ""}{decision.followedAi === true && <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">Followed AI</span>}{decision.followedAi === false && <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">Overrode AI</span>}</p>}
      {decision.comment && <p className="mt-3 whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{decision.comment}</p>}
      {(decision.aiRating || decision.agentFeedback) && <div className="mt-3 rounded-lg border border-cyan-100 bg-cyan-50/40 p-3 text-sm"><p className="font-semibold text-cyan-800">Feedback for the agents{decision.aiRating ? `: ${decision.aiRating}` : ""}</p>{decision.agentFeedback && <p className="mt-1 whitespace-pre-line text-slate-700">{decision.agentFeedback}</p>}</div>}
      {stale && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">The AI assessment has been re-run since this decision. Review the new result and change the decision if needed.</p>}
      <button type="button" disabled={reopening} onClick={() => startReopen(async () => setReopenError((await reopenDecision(applicationId)).error))} className="mt-4 text-sm font-semibold text-cyan-700 hover:underline disabled:opacity-60">{reopening ? "Reopening…" : "Change decision"}</button>
      {reopenError && <p role="alert" className="mt-2 text-sm text-rose-700">{reopenError}</p>}
    </section>;
  }

  return <form action={formAction} className="rounded-xl border-2 border-slate-900 bg-white p-6 shadow-sm">
    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Step 3 · Recruiter approval</p>
    <h2 className="mt-1 font-bold">Your decision</h2>
    {aiRunning ? <p className="mt-2 rounded-lg bg-blue-50 p-3 text-sm text-blue-800">The AI assessment is still running. You can decide once the reviewer has finished.</p>
      : recommendation ? <p className="mt-2 text-sm text-slate-600">{reviewed ? "Validated AI recommendation" : "AI recommendation (not reviewed)"}: <strong className="text-slate-900">{recommendation}</strong>{score !== undefined ? ` · ${score}/100` : ""}. The AI advises; you decide.</p>
      : <p className="mt-2 text-sm text-slate-600">There is no AI recommendation. Review the resume and decide.</p>}

    {requiresRating && <fieldset className="mt-5">
      <legend className="text-sm font-medium text-slate-700">How accurate was the AI assessment? <span className="text-rose-600">*</span></legend>
      <div className="mt-2 grid grid-cols-3 gap-2">{["Accurate", "Partially accurate", "Inaccurate"].map((rating) => <label key={rating} className="flex cursor-pointer items-center justify-center rounded-lg border border-slate-300 px-2 py-2 text-center text-xs font-semibold text-slate-700 has-[:checked]:border-cyan-600 has-[:checked]:bg-cyan-50 has-[:checked]:text-cyan-800">      <input type="radio" name="aiRating" value={rating} required checked={aiRating === rating} onChange={() => setAiRating(rating)} className="sr-only" />{rating}</label>)}</div>
    </fieldset>}
          <label className="mt-4 block text-sm font-medium text-slate-700">Feedback for the agents (optional)<textarea name="agentFeedback" rows={2} maxLength={2000} value={agentFeedback} onChange={(event) => setAgentFeedback(event.target.value)} placeholder="What did the AI get right or wrong? This is used to improve the agents." className={fieldClass} /></label>
          <label className="mt-4 block text-sm font-medium text-slate-700">Decision comment (optional)<textarea name="comment" rows={2} maxLength={1000} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Why are you advancing or rejecting this candidate?" className={fieldClass} /></label>
    {state.error && <p role="alert" className="mt-3 text-sm text-rose-700">{state.error}</p>}
    <div className="mt-4 grid grid-cols-2 gap-3">
      <button type="submit" name="decision" value="Rejected" disabled={pending || aiRunning} className="rounded-lg border border-rose-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-700 disabled:opacity-60">Reject</button>
      <button type="submit" name="decision" value="Advanced" disabled={pending || aiRunning} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{pending ? "Saving…" : "Advance"}</button>
    </div>
  </form>;
}
