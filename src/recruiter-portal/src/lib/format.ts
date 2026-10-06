/** Shared date formatting so server and client render application dates identically. */
const dateTime = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Madrid" });
const dateOnly = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "Europe/Madrid" });

export const formatDateTime = (value: string) => dateTime.format(new Date(value));
export const formatDate = (value: string) => dateOnly.format(new Date(value));

/** Initials for a candidate avatar. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase() || "?";
}
