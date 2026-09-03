import { agentExecutions } from "@/data/mock-data";
import { StatusBadge } from "@/components/ui";

const evaluations = [["Candidate relevance", "0.91", "Pass", "142 runs"], ["Groundedness", "0.96", "Pass", "142 runs"], ["Safety review", "0.99", "Pass", "142 runs"]];
const traces = [["13:24:10", "Candidate evaluation", "Retrieved job criteria", "184ms"], ["13:24:11", "Candidate evaluation", "Analyzed resume evidence", "6.4s"], ["13:24:18", "Candidate review", "Created recruiter summary", "4.1s"]];

function formatDuration(durationMs?: number) { return durationMs === undefined ? "—" : `${(durationMs / 1000).toFixed(1)}s`; }
function formatCost(cost?: number) { return cost === undefined ? "—" : `$${cost.toFixed(3)}`; }

export default function OperationsPage() {
  return <>
    <div className="mb-8"><p className="text-sm font-medium text-cyan-700">Azure AI Foundry demo</p><h1 className="mt-1 text-3xl font-bold tracking-tight">AI Operations Center</h1><p className="mt-2 text-slate-500">Inspect agent executions, quality signals, traces, and estimated usage costs.</p></div>
    <section className="grid gap-4 md:grid-cols-3"><div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Agent runs today</p><p className="mt-2 text-3xl font-bold">47</p><p className="mt-2 text-xs font-medium text-emerald-600">98% completed successfully</p></div><div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Average latency</p><p className="mt-2 text-3xl font-bold">11.8s</p><p className="mt-2 text-xs font-medium text-slate-500">Across 3 agent workflows</p></div><div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Estimated spend today</p><p className="mt-2 text-3xl font-bold">$6.42</p><p className="mt-2 text-xs font-medium text-slate-500">1.2M tokens processed</p></div></section>
    <section className="mt-7 grid gap-7 xl:grid-cols-[1.2fr_.8fr]">
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><div className="border-b border-slate-100 p-5"><h2 className="font-bold">Recent agent executions</h2><p className="mt-1 text-sm text-slate-500">Inspectable mock execution records</p></div><div className="divide-y divide-slate-100">{agentExecutions.map((run) => <div key={run.id} className="grid grid-cols-[1fr_auto] gap-3 p-5 sm:grid-cols-4"><div><p className="font-semibold">{run.agentName}</p><p className="mt-1 font-mono text-xs text-slate-500">{run.id}</p></div><p className="text-sm text-slate-600">{run.model}</p><p className="text-sm text-slate-600">{formatDuration(run.durationMs)} · {formatCost(run.estimatedCostUsd)}</p><StatusBadge status={run.status} /></div>)}</div></div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-bold">Evaluation quality</h2><div className="mt-4 divide-y divide-slate-100">{evaluations.map(([name, score, status, runs]) => <div key={name} className="py-4"><div className="flex justify-between"><span className="font-medium">{name}</span><span className="font-bold text-emerald-700">{score}</span></div><p className="mt-1 text-xs text-slate-500">{status} · {runs}</p></div>)}</div></div>
    </section>
    <section className="mt-7 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-bold">Latest trace</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-150 text-left text-sm"><tbody className="divide-y divide-slate-100">{traces.map(([time, agent, event, duration]) => <tr key={`${time}-${event}`}><td className="py-3 font-mono text-xs text-slate-500">{time}</td><td className="py-3 font-medium">{agent}</td><td className="py-3 text-slate-600">{event}</td><td className="py-3 text-right text-slate-500">{duration}</td></tr>)}</tbody></table></div></section>
  </>;
}
