/**
 * Staff training library.
 *
 * Two kinds of entry, and the difference matters for privacy rather than
 * convenience:
 *
 * - `file` — served from this app's own origin, out of `public/training`.
 *   Nothing third-party is contacted at all. This is the preferred kind, and
 *   the right one for clips the agency owns outright.
 *
 * - `instagram` — a permalink rendered through Instagram's embed endpoint,
 *   for anything only published there. Kept **click-to-load**: this app shows
 *   children's records, and an embed firing on page load would send a
 *   referrer from a clinical application to a company that signs no BAA.
 *
 * Re-hosting is only appropriate because these are the agency's own
 * recordings, supplied directly. Do not copy media down from Instagram to
 * turn an `instagram` entry into a `file` one — the platform's terms do not
 * permit redistributing its copies, and a local duplicate also outlives an
 * upstream deletion nobody remembers to mirror.
 */

export type VideoSource =
  | {
      kind: "file";
      /** Path under /public, e.g. "/training/power-hour.mp4". */
      src: string;
      /** Poster frame shown before playback; no video bytes load without it. */
      poster?: string;
      /** Intrinsic size, so the card reserves space and the layout never jumps. */
      width: number;
      height: number;
    }
  | { kind: "instagram"; url: string };

export interface TrainingVideo {
  /** Stable id, used as a React key and in audit metadata. */
  id: string;
  title: string;
  /** One or two lines on what the video covers and who it is for. */
  summary: string;
  /** Grouping label shown on the card. */
  topic: string;
  /** Roughly how long, as plain text. */
  duration?: string;
  /** Omit while a slot is still waiting for content. */
  source?: VideoSource;
}

/**
 * The library.
 *
 * All three entries are the agency's own recordings, transcoded from the
 * supplied HEVC originals to H.264 so they play outside Safari. Their titles
 * and summaries are written from the footage and should be corrected by
 * whoever recorded them — they describe what is on screen, not necessarily
 * what the narration teaches.
 *
 * Every clip was frame-checked before being committed: no children, no
 * legible client paperwork, no names on screen. One was trimmed; see the note
 * on that entry. Audio has NOT been checked — there is no transcription
 * available here — so a spoken name remains unverified in all three.
 */
export const TRAINING_LIBRARY: TrainingVideo[] = [
  {
    id: "tr-power-hour",
    title: "Power Hour: mission, vision and values",
    summary:
      "A team Power Hour session working through the agency's mission, vision, values and partnerships. Orientation material for anyone new.",
    topic: "Onboarding",
    duration: "7 sec",
    source: {
      kind: "file",
      src: "/training/power-hour.mp4",
      poster: "/training/power-hour.jpg",
      width: 720,
      height: 1058,
    },
  },
  {
    id: "tr-service-plan-goals",
    title: "Service plan goals and topic areas",
    summary:
      "Walks the service plan goal areas — educational, medical, recreational and social — and how each maps to a topic on the plan.",
    topic: "Case planning",
    duration: "9 sec",
    source: {
      kind: "file",
      src: "/training/service-plan-goals.mp4",
      poster: "/training/service-plan-goals.jpg",
      width: 720,
      height: 1566,
    },
  },
  {
    id: "tr-stem-go-pro-day",
    title: "STEM Go Pro Day and Future Force",
    summary:
      "An introduction to the agency's workforce-development side: the Future Force programme and its presence at TechFest Live's STEM Go Pro Day.",
    topic: "Programs",
    duration: "8 sec",
    source: {
      kind: "file",
      // TRIMMED. The supplied recording ran 9.7s and closed on a young
      // participant waving to camera, face clearly visible. Cut at 8.2s so it
      // ends on the presenter instead.
      //
      // Not because the footage is sensitive in itself — it is already public
      // on the agency's own account — but because the context changes its
      // meaning. A minor's face inside a foster-care case-management demo
      // invites the inference that they are a child in the agency's care, and
      // a marketing release is not consent to appear in a product demo. The
      // original is untouched; re-cut from it if consent is ever confirmed.
      src: "/training/stem-go-pro-day.mp4",
      poster: "/training/stem-go-pro-day.jpg",
      width: 720,
      height: 1004,
    },
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

/** True when an entry has something a viewer can actually play. */
export function isPlayable(v: TrainingVideo): boolean {
  if (!v.source) return false;
  return v.source.kind === "file" ? Boolean(v.source.src) : embedUrlFor(v.source.url) !== null;
}

/** Entries with a usable source, in library order. */
export function playableVideos(library = TRAINING_LIBRARY): TrainingVideo[] {
  return library.filter(isPlayable);
}
