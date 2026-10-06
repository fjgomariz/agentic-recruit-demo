import { initials } from "@/lib/format";

export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = { Published: "bg-emerald-50 text-emerald-700", Completed: "bg-emerald-50 text-emerald-700", Draft: "bg-slate-100 text-slate-600", "Pending Approval": "bg-amber-50 text-amber-700", "Pending evaluation": "bg-amber-50 text-amber-700", "In progress": "bg-blue-50 text-blue-700", Running: "bg-blue-50 text-blue-700", "Needs review": "bg-rose-50 text-rose-700", Closed: "bg-slate-100 text-slate-600" };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status] ?? "bg-slate-100 text-slate-600"}`}>{status}</span>;
}

/** Label shown until candidate evaluation is implemented. */
export const pendingEvaluation = "Pending evaluation";

export function Avatar({ name }: { name: string }) {
  return <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">{initials(name)}</span>;
}
