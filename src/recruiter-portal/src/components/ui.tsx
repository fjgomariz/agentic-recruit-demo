import { initials } from "@/lib/format";

const badgeStyles: Record<string, string> = {
  Published: "bg-emerald-50 text-emerald-700",
  Completed: "bg-emerald-50 text-emerald-700",
  Draft: "bg-slate-100 text-slate-600",
  "Pending Approval": "bg-amber-50 text-amber-700",
  "Pending evaluation": "bg-slate-100 text-slate-600",
  "Evaluating…": "bg-blue-50 text-blue-700",
  "Evaluation failed": "bg-rose-50 text-rose-700",
  "Strong match": "bg-emerald-50 text-emerald-700",
  "Possible match": "bg-amber-50 text-amber-700",
  "Not a match": "bg-slate-100 text-slate-600",
  "Needs manual review": "bg-rose-50 text-rose-700",
  Advanced: "bg-emerald-600 text-white",
  Rejected: "bg-slate-700 text-white",
  "In progress": "bg-blue-50 text-blue-700",
  Running: "bg-blue-50 text-blue-700",
  Failed: "bg-rose-50 text-rose-700",
  "Needs review": "bg-rose-50 text-rose-700",
  Closed: "bg-slate-100 text-slate-600",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${badgeStyles[status] ?? "bg-slate-100 text-slate-600"}`}>{status}</span>;
}

/** Circular 0-100 score; a dash when the application has not been scored. */
export function Score({ value, size = "md" }: { value?: number; size?: "md" | "lg" }) {
  const tone = value === undefined ? "bg-slate-100 text-slate-400" : value >= 80 ? "bg-emerald-100 text-emerald-700" : value >= 55 ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700";
  const dimensions = size === "lg" ? "h-16 w-16 text-xl" : "h-10 w-10 text-xs";
  return <span title={value === undefined ? "Not scored" : `AI score ${value}/100`} className={`grid shrink-0 place-items-center rounded-full font-bold ${dimensions} ${tone}`}>{value ?? "—"}</span>;
}

export function Avatar({ name }: { name: string }) {
  return <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">{initials(name)}</span>;
}
