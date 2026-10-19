export interface CurrentUser {
  name: string;
  email?: string;
  initials: string;
}

/**
 * The portal has no sign-in: access is limited by an IP allow list on the ingress, so every request is the
 * demo recruiter. Decisions are recorded under this name.
 */
const demoRecruiter: CurrentUser = { name: "Jordan Lee", initials: "JL" };

export async function currentUser(): Promise<CurrentUser> {
  return demoRecruiter;
}
