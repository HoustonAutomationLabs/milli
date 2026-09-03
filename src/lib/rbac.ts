/**
 * Role-based access control.
 *
 * Three roles map to the three audiences in the strategy brief. Access is
 * enforced by *data scoping* (which records a user may read) on top of coarse
 * route permissions — the "minimum necessary" principle that HIPAA requires.
 *
 * This is the single source of truth for what each role can see. Keep server
 * data access gated through `scopeForUser()` so a UI bug can never widen access.
 */

export type Role = "ceo" | "manager" | "staff";

export const ROLES: Role[] = ["ceo", "manager", "staff"];

export interface AuthUser {
  id: string;
  name: string;
  role: Role;
  /** Teams this user manages (managers) or belongs to (staff). Empty for CEO. */
  teamIds: string[];
  /** The caseworker record this user maps to, if they carry a caseload. */
  caseworkerId?: string;
}

/** Coarse feature permissions per role. Data scoping is handled separately. */
export const PERMISSIONS = {
  ceo: {
    label: "Executive",
    viewAgencyKpis: true,
    viewAllTeams: true,
    viewComplianceRegister: true,
    viewHomesRegister: true,
    manageUsers: true,
  },
  manager: {
    label: "Manager",
    viewAgencyKpis: false,
    viewAllTeams: false,
    viewComplianceRegister: true,
    viewHomesRegister: true,
    manageUsers: false,
  },
  staff: {
    label: "Caseworker",
    viewAgencyKpis: false,
    viewAllTeams: false,
    viewComplianceRegister: false,
    viewHomesRegister: false,
    manageUsers: false,
  },
} as const;

export function can(user: AuthUser, permission: keyof (typeof PERMISSIONS)["ceo"]): boolean {
  const perms = PERMISSIONS[user.role];
  return Boolean((perms as Record<string, unknown>)[permission]);
}

/**
 * The data scope a user is allowed to read. Every data-layer query MUST filter
 * against this so no role can read beyond its lane.
 */
export interface DataScope {
  role: Role;
  /** true => may read every case in the agency (CEO only). */
  allCases: boolean;
  /** Team ids the user may read across. */
  teamIds: string[];
  /** Caseworker id the user is limited to (staff), if any. */
  caseworkerId?: string;
}

export function scopeForUser(user: AuthUser): DataScope {
  switch (user.role) {
    case "ceo":
      return { role: "ceo", allCases: true, teamIds: [] };
    case "manager":
      return { role: "manager", allCases: false, teamIds: user.teamIds };
    case "staff":
      return {
        role: "staff",
        allCases: false,
        teamIds: user.teamIds,
        caseworkerId: user.caseworkerId,
      };
  }
}
