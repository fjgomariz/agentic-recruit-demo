import Link from "next/link";

const navigation = [
  ["Overview", "/"], ["Jobs", "/jobs"], ["Candidates", "/candidates"], ["AI Operations", "/operations"],
];

export function PortalShell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-slate-50 text-slate-900"><aside className="fixed inset-y-0 hidden w-64 border-r border-slate-200 bg-slate-950 p-5 text-slate-300 lg:block"><Link href="/" className="mb-10 flex items-center gap-3 text-lg font-bold text-white"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-400 text-slate-950">N</span>Northstar</Link><p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Recruiting workspace</p><nav className="space-y-1">{navigation.map(([label, href]) => <Link key={href} href={href} className="block rounded-lg px-3 py-2.5 text-sm font-medium hover:bg-slate-800 hover:text-white">{label}</Link>)}</nav><div className="absolute bottom-6 left-5 right-5 rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs leading-5 text-slate-400">Demo environment<br /><span className="text-cyan-300">Synthetic data only</span></div></aside><div className="lg:pl-64"><header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-5 sm:px-8"><div className="text-sm text-slate-500">Talent acquisition <span className="mx-2 text-slate-300">/</span> Northstar</div><div className="flex items-center gap-3"><span className="hidden text-sm text-slate-500 sm:inline">Jordan Lee</span><span className="grid h-8 w-8 place-items-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">JL</span></div></header><main className="mx-auto max-w-7xl p-5 sm:p-8">{children}</main></div></div>;
}
