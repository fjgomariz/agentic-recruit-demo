import { headers } from "next/headers";

export interface CurrentUser {
  name: string;
  email?: string;
  initials: string;
  /** True when Container Apps authentication signed the user in; false in local development. */
  signedIn: boolean;
}

/** Shown when the portal runs locally without Container Apps authentication. */
const localUser: CurrentUser = { name: "Jordan Lee", initials: "JL", signedIn: false };

interface ClientPrincipal {
  claims?: { typ: string; val: string }[];
}

function initialsOf(name: string): string {
  return name.split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]!.toUpperCase()).join("") || "?";
}

/**
 * The signed-in recruiter, from the headers Container Apps authentication adds to every request.
 * The platform strips these headers from incoming requests, so they cannot be spoofed by the browser.
 */
export async function currentUser(): Promise<CurrentUser> {
  const requestHeaders = await headers();
  const email = requestHeaders.get("x-ms-client-principal-name") ?? undefined;
  if (!email) return localUser;
  let name = email;
  const encoded = requestHeaders.get("x-ms-client-principal");
  if (encoded) {
    try {
      const principal = JSON.parse(Buffer.from(encoded, "base64").toString("utf8")) as ClientPrincipal;
      name = principal.claims?.find((claim) => claim.typ === "name")?.val ?? email;
    } catch {
      // Keep the email as the display name.
    }
  }
  return { name, email, initials: initialsOf(name), signedIn: true };
}
