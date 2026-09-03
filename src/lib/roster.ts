/**
 * User roster — who is allowed to sign in, and what they see once they do.
 *
 * A Google Workspace login (once wired up in `auth.ts`) only proves *who*
 * someone is. It says nothing about whether they should have a dashboard
 * account, or which role/team they map to. This module is that missing
 * piece: an explicit allow-list of email -> role -> team, edited by the CEO
 * from `/admin/users` (gated by `can(user, "manageUsers")`), never granted
 * automatically just because someone has a company email address.
 *
 * ⚠️ Storage here is a local JSON file — fine for a single dev/preview
 * instance, wrong for Cloud Run in production: each instance can have its
 * own disk, and nothing survives a redeploy. BEFORE PRODUCTION, point this
 * at the same durable store the rest of the stack uses (a small database
 * table, or a Firestore/Cloud SQL row) — the read/write functions below are
 * the seam to swap; nothing outside this file should touch the JSON layout.
 */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import type { AuthUser, Role } from "./rbac";

export interface RosterEntry {
  /** Lower-cased, the join key. Will be the verified SSO email once real auth lands. */
  email: string;
  name: string;
  role: Role;
  /** Teams this person manages (manager) or belongs to (staff). Empty for CEO. */
  teamIds: string[];
  /** The caseworker record this person maps to, if any (staff, and managers who also carry a caseload). */
  caseworkerId?: string;
}

const ROSTER_PATH = process.env.ROSTER_PATH ?? "./data/roster.json";

function normaliseEmail(email: string): string {
  return email.trim().toLowerCase();
}

export async function loadRoster(): Promise<RosterEntry[]> {
  try {
    const raw = await readFile(ROSTER_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw err;
  }
}

async function saveRoster(entries: RosterEntry[]): Promise<void> {
  await mkdir(dirname(ROSTER_PATH), { recursive: true });
  await writeFile(ROSTER_PATH, JSON.stringify(entries, null, 2) + "\n", "utf8");
}

/** Add a new roster entry, or replace the existing one for that email. */
export async function upsertRosterEntry(entry: RosterEntry): Promise<void> {
  const email = normaliseEmail(entry.email);
  const entries = await loadRoster();
  const next = entries.filter((e) => e.email !== email);
  next.push({ ...entry, email });
  await saveRoster(next);
}

export async function removeRosterEntry(email: string): Promise<void> {
  const target = normaliseEmail(email);
  const entries = await loadRoster();
  await saveRoster(entries.filter((e) => e.email !== target));
}

/**
 * The AuthUser a verified SSO email resolves to, or null if that email is
 * not on the roster — i.e. not allowed to sign in at all. A real auth
 * provider's callback should call this immediately after verifying identity,
 * before issuing a session: an email Google can verify but that isn't on
 * this list must be refused, not defaulted to any role.
 */
export async function resolveRosterUser(email: string): Promise<AuthUser | null> {
  const entries = await loadRoster();
  const entry = entries.find((e) => e.email === normaliseEmail(email));
  if (!entry) return null;
  return {
    id: entry.email,
    name: entry.name,
    role: entry.role,
    teamIds: entry.teamIds,
    caseworkerId: entry.caseworkerId,
  };
}
