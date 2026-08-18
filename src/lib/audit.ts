/**
 * Audit logging for PHI access.
 *
 * HIPAA requires an audit trail of who accessed which protected records, when.
 * Every server-side read of case data should emit an audit event via
 * `recordAccess()`. In this scaffold events go to stdout (structured JSON);
 * in production point AUDIT_SINK at a durable, tamper-evident store
 * (WORM bucket, SIEM, append-only table) — never the same DB row the data
 * lives in, and never anywhere it can be silently edited.
 */

import type { AuthUser } from "./rbac";

export type AuditAction =
  | "login"
  | "logout"
  | "view_dashboard"
  | "view_caseload"
  | "view_case"
  | "view_compliance"
  | "denied";

export interface AuditEvent {
  ts: string;
  actorId: string;
  actorRole: string;
  action: AuditAction;
  /** Resource identifiers touched (case ids, team ids). No PHI values here. */
  resourceIds?: string[];
  /** Coarse outcome. */
  outcome: "allowed" | "denied";
  meta?: Record<string, string | number | boolean>;
}

const SINK = process.env.AUDIT_SINK ?? "stdout";

export function recordAccess(
  actor: Pick<AuthUser, "id" | "role">,
  action: AuditAction,
  opts: { resourceIds?: string[]; outcome?: "allowed" | "denied"; meta?: AuditEvent["meta"] } = {},
): void {
  const event: AuditEvent = {
    ts: new Date().toISOString(),
    actorId: actor.id,
    actorRole: actor.role,
    action,
    resourceIds: opts.resourceIds,
    outcome: opts.outcome ?? "allowed",
    meta: opts.meta,
  };

  // IMPORTANT: log identifiers only, never PHI field values (names, DOBs,
  // medical detail). The audit trail records *access*, not the data itself.
  if (SINK === "stdout") {
    // eslint-disable-next-line no-console
    console.log(`[audit] ${JSON.stringify(event)}`);
  } else {
    // TODO(phase-0/1): ship to the configured durable sink.
    // eslint-disable-next-line no-console
    console.log(`[audit:${SINK}] ${JSON.stringify(event)}`);
  }
}
