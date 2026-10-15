"use client";

import { Fragment, useState, useTransition, type ReactNode } from "react";
import { searchTalentPool } from "@/app/jobs/actions";
import type { RetrievalStep, TalentMatchResult, TalentMatchSource } from "@/data/jobs";

const inputClass = "mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-cyan-600 focus:outline-none focus:ring-2 focus:ring-cyan-100";
const numberFormat = new Intl.NumberFormat("en-GB");
const seconds = (ms?: number | null) => (ms == null ? "—" : `${(ms / 1000).toFixed(1)} s`);
const documentUrl = (source: TalentMatchSource) => `/knowledge-documents/${source.container}/${encodeURIComponent(source.fileName)}`;
const sourceLabel = (source: TalentMatchSource) => (source.container === "talent-pool" ? "Resume" : "Policy");

function SparkIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M12 2l1.8 5.6L19.5 9l-5.7 1.6L12 16l-1.8-5.4L4.5 9l5.7-1.4L12 2zm6.5 11l.9 2.6 2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.6z" /></svg>;
}

/** Bold text and [n] citation markers become elements; everything else stays plain text, so nothing is parsed as HTML. */
function Inline({ text, sources }: { text: string; sources: TalentMatchSource[] }) {
  return <>{text.split(/(\*\*[^*]+\*\*|\[\d+\])/g).map((part, index): ReactNode => {
    const bold = /^\*\*([^*]+)\*\*$/.exec(part);
    if (bold) return <strong key={index} className="font-semibold text-slate-900">{bold[1]}</strong>;
    const citation = /^\[(\d+)\]$/.exec(part);
    if (citation) {
      const source = sources.find((candidate) => candidate.id === Number(citation[1]));
      return source
        ? <a key={index} href={documentUrl(source)} target="_blank" rel="noreferrer" title={`${sourceLabel(source)}: ${source.title}`} className="ml-0.5 align-super text-[10px] font-bold text-cyan-700 hover:underline">[{source.id}]</a>
        : null;
    }
    return <Fragment key={index}>{part}</Fragment>;
  })}</>;
}

/** Renders the agent's short markdown: bullet lists, numbered lists and paragraphs. */
function Answer({ text, sources }: { text: string; sources: TalentMatchSource[] }) {
  const blocks: { kind: "list" | "paragraph"; lines: string[] }[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    const item = /^(?:[-*•]|\d+\.)\s+(.*)$/.exec(line);
    const last = blocks[blocks.length - 1];
    if (item) {
      if (last?.kind === "list") last.lines.push(item[1]);
      else blocks.push({ kind: "list", lines: [item[1]] });
    } else blocks.push({ kind: "paragraph", lines: [line.replace(/^#+\s*/, "")] });
  }
  return <div className="space-y-3 text-sm leading-6 text-slate-700">{blocks.map((block, index) => block.kind === "list"
    ? <ul key={index} className="space-y-2">{block.lines.map((line, row) => <li key={row} className="flex gap-3"><span className="font-bold text-cyan-600">•</span><span><Inline text={line} sources={sources} /></span></li>)}</ul>
    : <p key={index}><Inline text={block.lines[0]} sources={sources} /></p>)}</div>;
}

function StepRow({ step }: { step: RetrievalStep }) {
  if (step.kind === "planning") {
    return <li><span className="font-semibold text-slate-900">Plans the question</span> with {step.model ?? "an LLM"} · {seconds(step.elapsedMs)}{step.inputTokens != null && ` · ${numberFormat.format(step.inputTokens)} → ${numberFormat.format(step.outputTokens ?? 0)} tokens`}</li>;
  }
  if (step.kind === "reasoning") {
    return <li><span className="font-semibold text-slate-900">Reranks and merges</span> the results{step.reasoningTokens != null && ` · ${numberFormat.format(step.reasoningTokens)} reasoning tokens`}</li>;
  }
  return <li><span className="rounded bg-cyan-50 px-1.5 py-0.5 text-xs font-semibold text-cyan-800">{step.knowledgeSource}</span> <span className="font-medium text-slate-900">“{step.query}”</span> · {step.documentCount ?? 0} passages · {seconds(step.elapsedMs)}</li>;
}

function HowItSearched({ result }: { result: TalentMatchResult }) {
  const plan = result.retrievalPlan;
  const searches = plan?.steps.filter((step) => step.kind === "search") ?? [];
  const sourcesSearched = new Set(searches.map((step) => step.knowledgeSource)).size;
  return <details className="group rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
    <summary className="cursor-pointer font-semibold text-slate-900">How it searched{plan ? ` · ${searches.length} parallel queries across ${sourcesSearched} source${sourcesSearched === 1 ? "" : "s"}` : ""}</summary>
    <div className="mt-4 space-y-4">
      <div><p className="font-semibold text-slate-900">1. The agent asked the knowledge base</p><ul className="mt-2 space-y-1">{result.agentQueries.length ? result.agentQueries.map((query) => <li key={query}>“{query}”</li>) : <li>No query was recorded.</li>}</ul></div>
      <div><p className="font-semibold text-slate-900">2. The knowledge base broke it down{plan?.reasoningEffort ? ` (reasoning effort: ${plan.reasoningEffort})` : ""}</p>
        {plan ? <ul className="mt-2 space-y-2">{plan.steps.map((step, index) => <StepRow key={index} step={step} />)}</ul> : <p className="mt-2">The retrieval plan could not be read this time; the answer above is not affected.</p>}
        {plan && <p className="mt-3 text-xs text-slate-500">Replayed with the first question the agent sent, so passage counts and timings can differ slightly from the live run.</p>}
      </div>
    </div>
  </details>;
}

/** Finds past candidates for a job with Foundry IQ agentic retrieval and shows the answer with its sources. */
export function TalentPoolPanel({ jobId }: { jobId: string }) {
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<TalentMatchResult>();
  const [error, setError] = useState<string>();
  const [searching, startSearching] = useTransition();

  const search = () => {
    setError(undefined);
    startSearching(async () => {
      const outcome = await searchTalentPool(jobId, notes);
      if (outcome.result) setResult(outcome.result);
      else {
        setResult(undefined);
        setError(outcome.error);
      }
    });
  };

  return <section className="mt-7 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
    <div className="border-b border-slate-100 p-5">
      <div className="flex items-center gap-2"><h2 className="font-bold">Talent pool</h2><span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700"><SparkIcon />Foundry IQ</span></div>
      <p className="mt-1 text-sm text-slate-500">Find past candidates who fit this role and check them against our hiring policies. The recruiter copilot searches the resumes and the policies together and cites every source.</p>
    </div>
    <div className="p-5">
      <label className="block text-sm font-medium text-slate-700" htmlFor="talent-notes">Guidance for the search <span className="font-normal text-slate-400">(optional)</span></label>
      <textarea id="talent-notes" className={`${inputClass} min-h-[4.5rem]`} maxLength={500} value={notes} disabled={searching} onChange={(event) => setNotes(event.target.value)} placeholder="For example: German speakers only, or available within two months." />
      <div className="mt-3 flex items-center gap-3">
        <button type="button" onClick={search} disabled={searching} className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"><SparkIcon />{searching ? "Searching…" : result ? "Search again" : "Find matches in the talent pool"}</button>
        {searching && <p className="text-sm text-slate-500" role="status">The copilot is planning several queries across the talent pool and the policies. This takes 15 to 30 seconds.</p>}
      </div>
      {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700" role="alert">{error}</p>}
      {result && !searching && <div className="mt-6 space-y-5" aria-live="polite">
        <Answer text={result.answer} sources={result.sources} />
        {result.sources.length > 0 && <div><h3 className="text-sm font-bold text-slate-900">Sources</h3><ol className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200 text-sm">{result.sources.map((source) => <li key={source.id} className="flex items-center justify-between gap-3 px-3 py-2"><span><span className="font-bold text-cyan-700">[{source.id}]</span> <span className="font-medium text-slate-900">{source.title}</span> <span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{sourceLabel(source)}</span></span><a href={documentUrl(source)} target="_blank" rel="noreferrer" className="shrink-0 font-semibold text-cyan-700">Open</a></li>)}</ol></div>}
        <HowItSearched result={result} />
        <p className="text-xs text-slate-500">AI-generated advice from {result.agentName}{result.agentVersion ? ` v${result.agentVersion}` : ""} · {seconds(result.durationMs)}{result.inputTokens != null && ` · ${numberFormat.format(result.inputTokens)} in / ${numberFormat.format(result.outputTokens ?? 0)} out tokens`} · run {result.executionId}. {result.citationsAdjusted > 0 && `Every citation was checked against the sentence it supports; ${result.citationsAdjusted} that pointed at another document were corrected or removed. `}Confirm the candidate gave consent before contacting anyone.</p>
      </div>}
    </div>
  </section>;
}
