export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = { Published: "bg-emerald-50 text-emerald-700", Completed: "bg-emerald-50 text-emerald-700", Draft: "bg-slate-100 text-slate-600", "Pending Approval": "bg-amber-50 text-amber-700", "In progress": "bg-blue-50 text-blue-700", Running: "bg-blue-50 text-blue-700", "Needs review": "bg-rose-50 text-rose-700", Closed: "bg-slate-100 text-slate-600" };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status] ?? "bg-slate-100 text-slate-600"}`}>{status}</span>;
}

export function Score({ value }: { value: number }) {
  const tone = value >= 85 ? "bg-emerald-100 text-emerald-700" : value >= 75 ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700";
  return <span className={`grid h-10 w-10 place-items-center rounded-full text-xs font-bold ${tone}`}>{value}</span>;
}
