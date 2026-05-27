/**
 * Gmail OAuth token helpers — stored in browser localStorage.
 * Personal use only — this is the simplest and most practical approach.
 */

const KEYS = {
  token: "gmail_access_token",
  email: "gmail_user_email",
  name:  "gmail_user_name",
  picture: "gmail_user_picture",
} as const;

export interface GmailUser {
  token: string;
  email: string;
  name: string;
  picture: string;
}

/** Save OAuth result to localStorage after callback. */
export function saveAuth(user: GmailUser): void {
  localStorage.setItem(KEYS.token,   user.token);
  localStorage.setItem(KEYS.email,   user.email);
  localStorage.setItem(KEYS.name,    user.name);
  localStorage.setItem(KEYS.picture, user.picture);
}

/** Load saved auth from localStorage. Returns null if not authenticated. */
export function loadAuth(): GmailUser | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem(KEYS.token);
  if (!token) return null;
  return {
    token,
    email:   localStorage.getItem(KEYS.email)   ?? "",
    name:    localStorage.getItem(KEYS.name)     ?? "",
    picture: localStorage.getItem(KEYS.picture)  ?? "",
  };
}

/** Remove auth from localStorage (disconnect Gmail). */
export function clearAuth(): void {
  Object.values(KEYS).forEach((k) => localStorage.removeItem(k));
}

/** Returns true if user has a stored token. */
export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem(KEYS.token);
}
