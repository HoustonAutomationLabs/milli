/**
 * Staff training library.
 *
 * Videos are not hosted here. Each entry is a **permalink** to a post on the
 * agency's own Instagram account, and the page renders it through Instagram's
 * own embed endpoint. Two reasons that matters:
 *
 * 1. Re-hosting a copy would put the agency's media on the app's own origin.
 *    Instagram's terms do not permit redistributing platform copies, and the
 *    embed is the sanctioned way to show a post somewhere else — it keeps
 *    attribution, and a post deleted upstream disappears here too rather than
 *    living on in a stale copy nobody remembers to remove.
 *
 * 2. Nothing loads from Meta until a person clicks. This app renders
 *    children's records; dropping a Meta script or iframe into it on page
 *    load would hand Meta referrer and usage signals from a PHI application,
 *    and Meta signs no BAA for embeds. Click-to-load keeps that boundary
 *    explicit and under the user's control. See `VideoCard`.
 */

export interface TrainingVideo {
  /** Stable id, used as a React key and in audit metadata. */
  id: string;
  title: string;
  /** One or two lines on what the video covers and who it is for. */
  summary: string;
  /** Public Instagram permalink — /p/<code>/ or /reel/<code>/. */
  url: string;
  /** Grouping label shown on the card. */
  topic: string;
  /** Roughly how long, as plain text. Optional; omitted when unknown. */
  duration?: string;
}

/**
 * The library.
 *
 * DEMO CONTENT. Replace the three placeholder entries with real permalinks
 * from https://www.instagram.com/houstonstrongcpa — copy a post's "Copy link"
 * value straight in. Nothing else needs to change; the page is driven entirely
 * by this array and renders an explicit empty state when a url is blank.
 */
export const TRAINING_LIBRARY: TrainingVideo[] = [
  {
    id: "tr-01",
    title: "Placement day: what to have ready",
    summary:
      "Walks a new caseworker through the paperwork and the conversations that have to happen on the day a child is placed.",
    url: "",
    topic: "Onboarding",
  },
  {
    id: "tr-02",
    title: "Documenting a home visit",
    summary:
      "What a complete visit note looks like, and the fields that most often send a submission back for rework.",
    url: "",
    topic: "Documentation",
  },
  {
    id: "tr-03",
    title: "Reporting abuse or neglect",
    summary:
      "The mandatory-reporter obligation, the timeline it runs on, and who to notify inside the agency.",
    url: "",
    topic: "Compliance",
  },
];

/**
 * Turn a permalink into Instagram's embed URL, or null if it is not one.
 *
 * Deliberately strict, and an allowlist rather than a pattern-patch: this
 * value ends up in an iframe `src`, so anything that is not demonstrably an
 * Instagram post permalink must not reach it. If the library ever becomes
 * data-driven — pulled from a CMS, an export, or user input — this function is
 * the only thing standing between that data and an arbitrary framed origin.
 */
export function embedUrlFor(permalink: string): string | null {
  if (!permalink) return null;

  let parsed: URL;
  try {
    parsed = new URL(permalink);
  } catch {
    return null;
  }

  if (parsed.protocol !== "https:") return null;
  const host = parsed.hostname.toLowerCase();
  if (host !== "instagram.com" && host !== "www.instagram.com") return null;

  // /p/<code>/ and /reel/<code>/ are the two post shapes. The shortcode is
  // Instagram's base64url-ish alphabet; anything else is not a post.
  const m = parsed.pathname.match(/^\/(p|reel|tv)\/([A-Za-z0-9_-]{5,32})\/?$/);
  if (!m) return null;

  return `https://www.instagram.com/${m[1]}/${m[2]}/embed/`;
}

/** Entries with a usable permalink, in library order. */
export function playableVideos(library = TRAINING_LIBRARY): TrainingVideo[] {
  return library.filter((v) => embedUrlFor(v.url) !== null);
}
