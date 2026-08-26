# Security one-pager — rewrite

**Drafted:** 2026-08-25. Replaces the client-facing *Data Security &
Confidentiality Overview* currently circulating to prospects. Full version
published as an artifact.

## Why this was urgent

The circulating version promises point-in-time recovery that the free database
tier does not provide, multi-factor authentication that is switched off,
database-level tenant isolation that is not yet evaluating, and an absolute
("no employee error, software bug, or automation step can surface one firm's
data to another") that cannot honestly be claimed of any system.

The risk is not that a prospect catches it — it is that a prospect **relies** on
it. These are engineering firms; some will forward it to counsel or IT, and it
may end up referenced in a services agreement. An aspirational security document
converts a gap into a misrepresentation.

## Fix before sending

1. **Turn on MFA everywhere** — automation platform, database, document store,
   portal, password vault. Fifteen minutes, free.
2. **Move the listed contact to the company domain** — currently mismatched
   against the portal invite sender.
3. **Delete placeholder contacts and demo companies from the portal** — they
   undercut "access limited to named individuals."

Two values are the operator's decision, not facts: retention period after an
engagement ends, and incident notification window. Pick numbers that can
actually be met.

## Line-by-line

| Original claim | Status | Rewrite |
|---|---|---|
| Point-in-time recovery | Untrue | Daily encrypted backups only. Returns on a paid tier |
| MFA enforced everywhere | Untrue today | Kept — becomes true in 15 minutes. Fix first |
| Per-firm isolation enforced at database level | Aspirational | Describes the tenant identifier and policies honestly; states enforcement currently sits in the application. Fully true when per-firm tokens are minted |
| "No employee error, software bug, or automation step can..." | Unprovable | **Removed, not replaced.** A client's IT reviewer reads an absolute as evidence the rest was written carelessly |
| Role-based access limited to assigned personnel | True | Kept, made concrete — named individuals, same-day revocation, vault-held credentials |
| Contact on mismatched domain | Inconsistent | One address, company domain, matching the portal |

## Four additions

- **What we hold, and what we don't.** Naming the boundary reassures more than
  describing controls.
- **Conflict-of-interest position.** Two clients bidding the same solicitation —
  the question this market actually cares about, absent from the original.
  Answering it unprompted is a competitive advantage. Requires a policy
  decision: decline the second engagement, or accept with written disclosure to
  both and separate personnel.
- **Exit and deletion.** Standard procurement question, cheap to answer well.
- **Incident notification.** Committing to a first call before the picture is
  complete lands well because it is what a client actually wants.

## What returns later

- **Point-in-time recovery** — the day the database moves to a paid tier.
- **"Enforced at the database level"** — the day per-firm tokens are minted and
  the policies actually evaluate.

Both are already on the backlog.

## What does not return with a code change

Nothing here makes the platform suitable for data carrying a regulatory
obligation. Proposal content is commercially sensitive, not regulated, so this
is fine for the work at hand — but if a client asks for something covered by
statute, the honest answer is that the current arrangement is not built for it.
