"use client";

import { useActionState, useState, useTransition } from "react";
import type { ApplicationDecision } from "@domain";
import { recordDecision, reopenDecision, startEvaluation, type CandidateActionState } from "@/app/candidates/actions";
import { StatusBadge } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

export function EvaluateButton({ applicationId, label }: { applicationId: string; label: string }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string>();
  return <div>
    <button type="button" disabled={pending} onClick={() => startTransition(async () => setError((await startEvaluation(applicationId)).error))} className="inline-flex items-center gap-2 rounded-lg bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">
      <span aria-hidden="true">✦</span>{pending ? "Starting…" : label}
    </button>
    {error && <p role="alert" className="mt-2 text-sm text-rose-700">{error}</p>}
  </div>;
}

export function DecisionPanel({ applicationId, decision, recommendation }: { applicationId: string; decision?: ApplicationDecision | null; recommendation?: string }) {
  const [state, formAction, pending] = useActionState<CandidateActionState, FormData>(recordDecision.bind(null, applicationId), {});
  const [reopening, startReopen] = useTransition();
  const [reopenError, setReopenError] = useState<string>();

  if (decision) {
    return <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-3"><h2 className="font-bold">Your decision</h2><StatusBadge status={decision.status} /></div>
      <p className="mt-3 text-sm text-slate-600">{decision.decidedBy} · {formatDateTime(decision.decidedAt)}</p>
      {decision.comment && <p className="mt-3 whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{decision.comment}</p>}
      <button type="button" disabled={reopening} onClick={() => startReopen(async () => setReopenError((await reopenDecision(applicationId)).error))} className="mt-4 text-sm font-semibold text-cyan-700 hover:underline disabled:opacity-60">{reopening ? "Reopening…" : "Change decision"}</button>
      {reopenError && <p role="alert" className="mt-2 text-sm text-rose-700">{reopenError}</p>}
    </section>;
  }

  return <form action={formAction} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
    <h2 className="font-bold">Your decision</h2>
    <p className="mt-1 text-sm text-slate-500">{recommendation ? `The AI suggests “${recommendation}”. You decide.` : "Review the resume and decide."}</p>
    <label className="mt-4 block text-sm font-medium text-slate-700">Comment (optional)<textarea name="comment" rows={3} maxLength={1000} placeholder="Why are you advancing or rejecting this candidate?" className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-cyan-600 focus:outline-none focus:ring-2 focus:ring-cyan-100" /></label>
    {state.error && <p role="alert" className="mt-3 text-sm text-rose-700">{state.error}</p>}
    <div className="mt-4 grid grid-cols-2 gap-3">
      <button type="submit" name="decision" value="Rejected" disabled={pending} className="rounded-lg border border-rose-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-700 disabled:opacity-60">Reject</button>
      <button type="submit" name="decision" value="Advanced" disabled={pending} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{pending ? "Saving…" : "Advance"}</button>
    </div>
  </form>;
}
