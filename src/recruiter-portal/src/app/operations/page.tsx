import Link from "next/link";
import type { AgentExecution, AgentFeedback } from "@domain";
import { StatusBadge } from "@/components/ui";
import { getAgentExecutions, getAgentFeedback } from "@/data/jobs";
import { formatDateTime } from "@/lib/format";

const runsShown = 50;

const agentPurpose: Record<string, string> = {
  "job-description-writer": "Drafts job postings from recruiter notes",
  "candidate-evaluator": "Maker: scores resumes against job requirements",
  "candidate-evaluation-reviewer": "Checker: validates the evaluation, flags bias and overconfidence",
};

function seconds(durationMs?: number) {
  return durationMs === undefined ? "—" : `${(durationMs / 1000).toFixed(1)}s`;
}

function tokens(run: AgentExecution) {
  return run.inputTokens === undefined || run.inputTokens === null ? "—" : `${run.inputTokens.toLocaleString("en-GB")} in · ${(run.outputTokens ?? 0).toLocaleString("en-GB")} out`;
}

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : undefined;
}

function percent(part: number, whole: number) {
  return whole ? `${Math.round((part / whole) * 100)}%` : "—";
}

function FeedbackLoop({ feedback }: { feedback: AgentFeedback[] }) {
  const clearCut = feedback.filter((item) => item.followedAi !== null && item.followedAi !== undefined);
  const rated = feedback.filter((item) => item.aiRating);
  const reviewed = feedback.filter((item) => item.reviewerAgreement);
  const corrected = reviewed.filter((item) => item.reviewerAgreement !== "Agrees");
  const ratings = (["Accurate", "Partially accurate", "Inaccurate"] as const).map((rating) => [rating, rated.filter((item) => item.aiRating === rating).length] as const);
  const notes = feedback.filter((item) => item.agentFeedback);
  const metrics = [
    ["Recruiter decisions", String(feedback.length), "Human approvals recorded"],
    ["Followed the AI", percent(clearCut.filter((item) => item.followedAi).length, clearCut.length), `${clearCut.length} clear-cut recommendations`],
    ["Rated accurate", percent(ratings[0][1], rated.length), `${rated.length} AI assessments rated`],
    ["Reviewer corrections", percent(corrected.length, reviewed.length), `Evaluations the checker adjusted or disputed`],
  ];
  return <section className="mt-7 rounded-xl border border-slate-200 bg-white shadow-sm">
    <div className="border-b border-slate-100 p-5"><h2 className="font-bold">Human feedback loop</h2><p className="mt-1 text-sm text-slate-500">Recruiter approvals and ratings of the AI assessments, by agent version. Use them to tune prompts and to build evaluation datasets. No candidate personal data is included.</p></div>
    <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, detail]) => <div key={label} className="rounded-lg bg-slate-50 p-4"><p className="text-sm text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div>)}</div>
    {rated.length > 0 && <div className="px-5 pb-2"><div className="flex h-3 overflow-hidden rounded-full bg-slate-100" aria-label="AI assessment ratings">{ratings.map(([rating, count]) => count > 0 && <span key={rating} title={`${rating}: ${count}`} style={{ width: `${(count / rated.length) * 100}%` }} className={rating === "Accurate" ? "bg-emerald-500" : rating === "Partially accurate" ? "bg-amber-400" : "bg-rose-500"} />)}</div><p className="mt-2 text-xs text-slate-500">{ratings.map(([rating, count]) => `${rating}: ${count}`).join(" · ")}</p></div>}
    {notes.length === 0 ? <p className="p-5 text-sm text-slate-500">No written feedback yet. Recruiters can add feedback for the agents when they approve a candidate.</p> :
    <ul className="divide-y divide-slate-100 border-t border-slate-100">{notes.slice(0, 8).map((item) => <li key={item.applicationId} className="grid gap-2 p-5 md:grid-cols-[1fr_auto]">
      <div><p className="text-sm text-slate-800">“{item.agentFeedback}”</p><p className="mt-1 text-xs text-slate-500">{formatDateTime(item.decidedAt)} · {item.jobId} · evaluator v{item.evaluatorVersion ?? "?"}{item.reviewerVersion ? ` · reviewer v${item.reviewerVersion}` : ""} · AI {item.aiRecommendation ?? "—"} ({item.evaluationScore ?? "—"}{item.validatedScore !== null && item.validatedScore !== undefined ? ` → ${item.validatedScore}` : ""})</p></div>
      <div className="flex flex-wrap items-start gap-2 md:justify-end">{item.aiRating && <StatusBadge status={item.aiRating} />}<StatusBadge status={item.decision} />{item.followedAi === false && <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">Overrode AI</span>}</div>
    </li>)}</ul>}
  </section>;
}

export default async function OperationsPage() {
  const [runs, feedback] = await Promise.all([getAgentExecutions(runsShown), getAgentFeedback().catch(() => [] as AgentFeedback[])]);
  const completed = runs.filter((run) => run.status === "Completed");
  const totalTokens = runs.reduce((sum, run) => sum + (run.inputTokens ?? 0) + (run.outputTokens ?? 0), 0);
  const agents = [...new Set([...Object.keys(agentPurpose), ...runs.map((run) => run.agentName)])].map((name) => {
    const agentRuns = runs.filter((run) => run.agentName === name);
    return {
      name,
      runs: agentRuns.length,
      problems: agentRuns.filter((run) => run.status !== "Completed").length,
      latency: average(agentRuns.filter((run) => run.status === "Completed").map((run) => run.durationMs ?? 0)),
      version: agentRuns.find((run) => run.configurationVersion !== "unknown")?.configurationVersion,
      model: agentRuns.find((run) => run.configurationVersion !== "unknown")?.model,
    };
  });
  const models = [...new Set(runs.map((run) => run.model.replace(/-\d{4}-\d{2}-\d{2}$/, "")))];

  const metrics = [
    ["Agent runs", String(runs.length), `Last ${runsShown} recorded runs`],
    ["Completed", runs.length ? `${Math.round((completed.length / runs.length) * 100)}%` : "—", `${runs.length - completed.length} failed or flagged for review`],
    ["Average latency", seconds(average(completed.map((run) => run.durationMs ?? 0))), "Completed runs, end to end"],
    ["Tokens", totalTokens.toLocaleString("en-GB"), `Input and output · ${models.join(", ") || "no runs"}`],
  ];

  return <>
    <div className="mb-8"><p className="text-sm font-medium text-cyan-700">Microsoft Foundry</p><h1 className="mt-1 text-3xl font-bold tracking-tight">AI Operations</h1><p className="mt-2 text-slate-500">Every agent run recorded by the API, and the feedback recruiters give on the AI assessments. Detailed traces are in the Foundry portal (Agents → Traces) and Application Insights.</p></div>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, detail]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p><p className="mt-2 text-xs font-medium text-slate-500">{detail}</p></div>)}</section>
    <section className="mt-7 grid gap-4 md:grid-cols-3">{agents.map((agent) => <div key={agent.name} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3"><p className="font-mono text-sm font-semibold">{agent.name}</p>{agent.version && <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-700">{agent.version}</span>}</div>
      <p className="mt-1 text-sm text-slate-500">{agentPurpose[agent.name] ?? "Foundry prompt agent"}</p>
      {agent.model && <p className="mt-2 font-mono text-xs text-slate-500">{agent.model}</p>}
      <dl className="mt-4 grid grid-cols-3 gap-3 text-sm"><div><dt className="text-slate-500">Runs</dt><dd className="mt-1 font-semibold">{agent.runs}</dd></div><div><dt className="text-slate-500">Avg latency</dt><dd className="mt-1 font-semibold">{seconds(agent.latency)}</dd></div><div><dt className="text-slate-500">Issues</dt><dd className={`mt-1 font-semibold ${agent.problems ? "text-rose-700" : ""}`}>{agent.problems}</dd></div></dl>
    </div>)}</section>
    <FeedbackLoop feedback={feedback} />
    <section className="mt-7 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-5"><h2 className="font-bold">Recent agent runs</h2><p className="mt-1 text-sm text-slate-500">Newest first. Candidate content is not stored here.</p></div>
      {runs.length === 0 ? <p className="p-8 text-center text-sm text-slate-500">No agent runs yet. Generate a job description or receive an application to see runs here.</p> :
      <div className="overflow-x-auto"><table className="w-full min-w-200 text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Started</th><th className="px-5 py-3 font-semibold">Agent</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 font-semibold">Duration</th><th className="px-5 py-3 font-semibold">Tokens</th><th className="px-5 py-3 font-semibold">Outcome</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{runs.map((run) => <tr key={run.id} className="align-top">
          <td className="whitespace-nowrap px-5 py-4 text-slate-600">{formatDateTime(run.startedAt)}</td>
          <td className="px-5 py-4"><p className="font-mono text-xs font-semibold">{run.agentName}</p><p className="mt-1 text-xs text-slate-500">{run.configurationVersion} · {run.model}</p></td>
          <td className="px-5 py-4"><StatusBadge status={run.status} /></td>
          <td className="whitespace-nowrap px-5 py-4 text-slate-600">{seconds(run.durationMs)}</td>
          <td className="whitespace-nowrap px-5 py-4 text-slate-600">{tokens(run)}</td>
          <td className="px-5 py-4"><p className={run.errorMessage ? "text-rose-700" : "text-slate-700"}>{run.errorMessage ?? run.outputSummary ?? "—"}</p>{run.agentName.startsWith("candidate-") && run.relatedEntityIds[0] && <Link href={`/candidates/${run.relatedEntityIds[0]}`} className="mt-1 inline-block text-xs font-semibold text-cyan-700 hover:underline">Open candidate</Link>}<p className="mt-1 break-all font-mono text-[11px] text-slate-400">{run.id}</p></td>
        </tr>)}</tbody>
      </table></div>}
    </section>
  </>;
}
