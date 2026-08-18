/**
 * Authentication — DEV/MOCK provider.
 *
 * ⚠️ This is a scaffold. It signs a lightweight session cookie for local
 * development so the role-based UI can be exercised without a live IdP.
 *
 * BEFORE ANY PRODUCTION / PHI USE, replace this with a BAA-capable identity
 * provider (WorkOS, AWS Cognito, Okta, Microsoft Entra, etc.):
 *   - real credential handling + MFA
 *   - SSO / SCIM user provisioning
 *   - short session lifetimes and idle timeout
 * The rest of the app only depends on `getCurrentUser()` returning an
 * `AuthUser`, so swapping the provider does not ripple outward.
 */

import { cookies } from "next/headers";
import { createHmac, timingSafeEqual } from "crypto";
import type { AuthUser, Role } from "./rbac";
import { MOCK_USERS } from "./zoho/mock";

const COOKIE_NAME = "milli_session";
const SECRET = process.env.AUTH_SESSION_SECRET ?? "dev-insecure-secret";

function sign(value: string): string {
  return createHmac("sha256", SECRET).update(value).digest("base64url");
}

function serialize(userId: string): string {
  return `${userId}.${sign(userId)}`;
}

function verify(token: string | undefined): string | null {
  if (!token) return null;
  const idx = token.lastIndexOf(".");
  if (idx <= 0) return null;
  const userId = token.slice(0, idx);
  const mac = token.slice(idx + 1);
  const expected = sign(userId);
  const a = new Uint8Array(Buffer.from(mac));
  const b = new Uint8Array(Buffer.from(expected));
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  return userId;
}

/** Look up the signed-in user from the session cookie. Server-side only. */
export async function getCurrentUser(): Promise<AuthUser | null> {
  const store = await cookies();
  const userId = verify(store.get(COOKIE_NAME)?.value);
  if (!userId) return null;
  return MOCK_USERS.find((u) => u.id === userId) ?? null;
}

/** DEV: the accounts a tester can sign in as, one per role. */
export function listMockAccounts(): AuthUser[] {
  return MOCK_USERS;
}

export function sessionCookie(userId: string) {
  return {
    name: COOKIE_NAME,
    value: serialize(userId),
    options: {
      httpOnly: true,
      sameSite: "lax" as const,
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 8, // 8h — tighten for production
    },
  };
}

export function clearedCookie() {
  return { name: COOKIE_NAME, value: "", options: { path: "/", maxAge: 0 } };
}

export const AUTH_COOKIE_NAME = COOKIE_NAME;
export type { AuthUser, Role };
