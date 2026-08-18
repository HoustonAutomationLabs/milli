"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { clearedCookie, sessionCookie } from "@/lib/auth";
import { recordAccess } from "@/lib/audit";
import { MOCK_USERS } from "@/lib/zoho/mock";

/**
 * DEV sign-in. Picks one of the mock accounts by id and sets the session
 * cookie. Replace with a real IdP callback in production (see lib/auth.ts).
 */
export async function signIn(formData: FormData) {
  const userId = String(formData.get("userId") ?? "");
  const user = MOCK_USERS.find((u) => u.id === userId);
  if (!user) redirect("/login?error=unknown_account");

  const c = sessionCookie(user.id);
  (await cookies()).set(c.name, c.value, c.options);
  recordAccess({ id: user.id, role: user.role }, "login");
  redirect("/dashboard");
}

export async function signOut() {
  const c = clearedCookie();
  (await cookies()).set(c.name, c.value, c.options);
  redirect("/login");
}
