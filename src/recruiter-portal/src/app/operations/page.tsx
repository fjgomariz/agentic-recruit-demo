import Link from "next/link";
import type { AgentExecution } from "@domain";
import { StatusBadge } from "@/components/ui";
import { getAgentExecutions } from "@/data/jobs";
import { formatDateTime } from "@/lib/format";

const runsShown = 50;

const agentPurpose: Record<string, string> = {
  "job-description-writer": "Drafts job postings from recruiter notes",
  "candidate-evaluator": "Scores resumes against job requirements",
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

export default async function OperationsPage() {
  const runs = await getAgentExecutions(runsShown);
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
    };
  });

  const metrics = [
    ["Agent runs", String(runs.length), `Last ${runsShown} recorded runs`],
    ["Completed", runs.length ? `${Math.round((completed.length / runs.length) * 100)}%` : "—", `${runs.length - completed.length} failed or flagged for review`],
    ["Average latency", seconds(average(completed.map((run) => run.durationMs ?? 0))), "Completed runs, end to end"],
    ["Tokens", totalTokens.toLocaleString("en-GB"), "Input and output, gpt-5.4-mini"],
  ];

  return <>
    <div className="mb-8"><p className="text-sm font-medium text-cyan-700">Microsoft Foundry</p><h1 className="mt-1 text-3xl font-bold tracking-tight">AI Operations</h1><p className="mt-2 text-slate-500">Every agent run recorded by the API. Detailed traces are in the Foundry portal (Agents → Traces) and Application Insights.</p></div>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, detail]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p><p className="mt-2 text-xs font-medium text-slate-500">{detail}</p></div>)}</section>
    <section className="mt-7 grid gap-4 md:grid-cols-2">{agents.map((agent) => <div key={agent.name} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3"><p className="font-mono text-sm font-semibold">{agent.name}</p>{agent.version && <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-700">{agent.version}</span>}</div>
      <p className="mt-1 text-sm text-slate-500">{agentPurpose[agent.name] ?? "Foundry prompt agent"}</p>
      <dl className="mt-4 grid grid-cols-3 gap-3 text-sm"><div><dt className="text-slate-500">Runs</dt><dd className="mt-1 font-semibold">{agent.runs}</dd></div><div><dt className="text-slate-500">Avg latency</dt><dd className="mt-1 font-semibold">{seconds(agent.latency)}</dd></div><div><dt className="text-slate-500">Issues</dt><dd className={`mt-1 font-semibold ${agent.problems ? "text-rose-700" : ""}`}>{agent.problems}</dd></div></dl>
    </div>)}</section>
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
          <td className="px-5 py-4"><p className={run.errorMessage ? "text-rose-700" : "text-slate-700"}>{run.errorMessage ?? run.outputSummary ?? "—"}</p>{run.agentName === "candidate-evaluator" && run.relatedEntityIds[0] && <Link href={`/candidates/${run.relatedEntityIds[0]}`} className="mt-1 inline-block text-xs font-semibold text-cyan-700 hover:underline">Open candidate</Link>}<p className="mt-1 break-all font-mono text-[11px] text-slate-400">{run.id}</p></td>
        </tr>)}</tbody>
      </table></div>}
    </section>
  </>;
}
