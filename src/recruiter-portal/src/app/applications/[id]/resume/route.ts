import { downloadResume } from "@/data/jobs";

/** Proxies the private resume through the portal so the browser never talks to Blob Storage. */
export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const upstream = await downloadResume(id);
  if (!upstream.ok || !upstream.body) {
    return new Response(upstream.status === 404 ? "Resume not found." : "The resume could not be downloaded.", {
      status: upstream.status === 404 ? 404 : 502,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": upstream.headers.get("Content-Disposition") ?? `attachment; filename="${id}.pdf"`,
      "Cache-Control": "no-store",
    },
  });
}
