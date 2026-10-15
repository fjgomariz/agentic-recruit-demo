import { downloadKnowledgeDocument, knowledgeContainers } from "@/data/jobs";

/** Opens a talent pool resume or hiring policy cited by the recruiter copilot, proxied so the browser never talks to Blob Storage. */
export async function GET(_: Request, { params }: { params: Promise<{ container: string; file: string }> }) {
  const { container, file } = await params;
  if (!(knowledgeContainers as readonly string[]).includes(container)) {
    return new Response("Document not found.", { status: 404, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }

  const upstream = await downloadKnowledgeDocument(container, file);
  if (!upstream.ok || !upstream.body) {
    return new Response(upstream.status === 404 ? "Document not found." : "The document could not be downloaded.", {
      status: upstream.status === 404 ? 404 : 502,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "application/octet-stream",
      "Content-Disposition": upstream.headers.get("Content-Disposition") ?? `inline; filename="${file}"`,
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "no-store",
    },
  });
}
