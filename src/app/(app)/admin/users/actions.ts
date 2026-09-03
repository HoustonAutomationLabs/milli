"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { can, ROLES, type Role } from "@/lib/rbac";
import { recordAccess } from "@/lib/audit";
import { removeRosterEntry, upsertRosterEntry } from "@/lib/roster";

async function requireManager() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (!can(user, "manageUsers")) {
    recordAccess({ id: user.id, role: user.role }, "denied", { meta: { route: "admin/users" } });
    redirect("/dashboard");
  }
  return user;
}

export async function upsertUser(formData: FormData) {
  const actor = await requireManager();

  const email = String(formData.get("email") ?? "").trim();
  const name = String(formData.get("name") ?? "").trim();
  const role = String(formData.get("role") ?? "") as Role;
  const teamIds = formData
    .getAll("teamIds")
    .map((v) => String(v))
    .filter(Boolean);
  const caseworkerId = String(formData.get("caseworkerId") ?? "").trim() || undefined;

  if (!email || !name || !ROLES.includes(role)) {
    redirect("/admin/users?error=invalid");
  }

  await upsertRosterEntry({ email, name, role, teamIds, caseworkerId });
  recordAccess({ id: actor.id, role: actor.role }, "roster_update", {
    meta: { op: "upsert", email },
  });

  revalidatePath("/admin/users");
}

export async function deleteUser(formData: FormData) {
  const actor = await requireManager();
  const email = String(formData.get("email") ?? "").trim();
  if (!email) redirect("/admin/users?error=invalid");

  await removeRosterEntry(email);
  recordAccess({ id: actor.id, role: actor.role }, "roster_update", {
    meta: { op: "remove", email },
  });

  revalidatePath("/admin/users");
}
