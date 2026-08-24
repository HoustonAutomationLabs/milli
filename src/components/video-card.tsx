"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { embedUrlFor, type TrainingVideo } from "@/lib/training";

/**
 * One training video.
 *
 * Neither kind of source fetches anything until the viewer asks for it. A
 * local file uses `preload="none"`, so the poster is all that loads until
 * play is pressed. An Instagram entry renders no iframe at all until clicked,
 * because this app shows children's records and an embed firing on page load
 * would contact Meta on every view.
 */
export function VideoCard({ video }: { video: TrainingVideo }) {
  const [playing, setPlaying] = useState(false);
  const source = video.source;

  return (
    <Card className="flex flex-col">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-accent">
          {video.topic}
        </span>
        {video.duration ? (
          <span className="text-[13px] text-muted tnum">{video.duration}</span>
        ) : null}
      </div>

      <h3 className="mt-2 text-[17px] font-semibold leading-snug text-ink">{video.title}</h3>
      <p className="mt-1.5 flex-1 text-[14px] leading-relaxed text-ink-soft">{video.summary}</p>

      <div className="mt-4">
        {!source ? (
          <UnlinkedSlot />
        ) : source.kind === "file" ? (
          <div
            className="overflow-hidden rounded-xl border border-line bg-black"
            // Reserve the space the video will occupy so nothing reflows once
            // it loads. These clips are portrait and not all the same shape.
            style={{ aspectRatio: `${source.width} / ${source.height}` }}
          >
            <video
              className="h-full w-full"
              controls
              preload="none"
              playsInline
              poster={source.poster}
              // Capped so a tall portrait clip cannot dominate the card.
              style={{ objectFit: "contain", maxHeight: "460px" }}
            >
              <source src={source.src} type="video/mp4" />
              Your browser cannot play this video.
            </video>
          </div>
        ) : playing ? (
          <div className="overflow-hidden rounded-xl border border-line">
            {/* Fixed height: Instagram's embed does not report its own size to
                the parent, so there is nothing to resize against. */}
            <iframe
              src={embedUrlFor(source.url) ?? ""}
              title={video.title}
              className="block h-[540px] w-full border-0"
              loading="lazy"
              sandbox="allow-scripts allow-same-origin allow-presentation"
              referrerPolicy="no-referrer"
              allow="encrypted-media; picture-in-picture"
            />
          </div>
        ) : (
          <LoadButton onClick={() => setPlaying(true)} />
        )}
      </div>

      {source?.kind === "instagram" ? (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mt-3 text-[13px] font-medium text-accent hover:underline underline-offset-2"
        >
          Open on Instagram &rarr;
        </a>
      ) : null}
    </Card>
  );
}

function UnlinkedSlot() {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface-2 p-4">
      <div className="text-[13px] font-medium text-ink">No video linked yet</div>
      <p className="mt-1 text-[13px] leading-snug text-muted">
        Add a <code className="text-[12px]">source</code> for this entry in{" "}
        <code className="text-[12px]">src/lib/training.ts</code>.
      </p>
    </div>
  );
}

function LoadButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-center gap-3 rounded-xl border border-line bg-surface-2 px-4 py-3 text-left hover:border-accent"
    >
      <span
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
        style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
        aria-hidden
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
          <path d="M8 5.5v13l11-6.5z" />
        </svg>
      </span>
      <span className="min-w-0">
        <span className="block text-[14px] font-medium text-ink">Load video</span>
        <span className="block text-[12px] text-muted">Loads from Instagram when you click</span>
      </span>
    </button>
  );
}
