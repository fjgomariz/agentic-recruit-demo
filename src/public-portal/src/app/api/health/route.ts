/**
 * Unauthenticated health check used by the deployment pipeline (the only path excluded from sign-in).
 * It confirms the portal can reach the internal API and the API can read Cosmos DB, without returning any data.
 */
export const dynamic = "force-dynamic";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(): Promise<Response> {
  try {
    const response = await fetch(`${apiBaseUrl}/jobs`, { cache: "no-store", signal: AbortSignal.timeout(10_000) });
    return Response.json({ status: response.ok ? "healthy" : "degraded", api: response.ok ? "reachable" : `HTTP ${response.status}` }, { status: response.ok ? 200 : 503 });
  } catch {
    return Response.json({ status: "degraded", api: "unreachable" }, { status: 503 });
  }
}
