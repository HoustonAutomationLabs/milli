import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { recordAccess } from "@/lib/audit";
import { Card, SectionTitle } from "@/components/ui";
import { VideoCard } from "@/components/video-card";
import { TRAINING_LIBRARY, playableVideos } from "@/lib/training";

export const metadata = { title: "Training" };

export default async function TrainingPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  // Deliberately no role gate. Training is the one thing in this app every
  // role needs equally, and it contains no case data — so unlike every other
  // page, there is nothing here to scope.
  const playable = playableVideos();

  recordAccess({ id: user.id, role: user.role }, "view_training", {
    meta: { videos: TRAINING_LIBRARY.length, playable: playable.length },
  });

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Training</h1>
        <p className="mt-1 max-w-3xl text-[15px] text-ink-soft">
          Short videos from the agency&rsquo;s own channel, for every role. Nothing
          here is case data, so the whole library is visible to everyone.
        </p>
      </header>

      {playable.length === 0 ? (
        <Card className="mb-6 border-l-4" style={{ borderLeftColor: "var(--warn)" }}>
          <SectionTitle>Library not yet linked</SectionTitle>
          <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink-soft">
            The three slots below are placeholders. Add each video&rsquo;s Instagram
            permalink &mdash; the value behind &ldquo;Copy link&rdquo; on the post
            &mdash; to <code className="text-[13px]">TRAINING_LIBRARY</code> in{" "}
            <code className="text-[13px]">src/lib/training.ts</code>. Only
            instagram.com post and reel links are accepted; anything else is
            rejected rather than framed.
          </p>
        </Card>
      ) : null}

      <section className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {TRAINING_LIBRARY.map((v) => (
          <VideoCard key={v.id} video={v} />
        ))}
      </section>

      <Card className="mt-6">
        <SectionTitle>How this library works</SectionTitle>
        <ul className="mt-3 flex flex-col gap-2 text-[14px] leading-relaxed text-ink-soft">
          <li>
            Videos are <strong className="font-semibold text-ink">not copied here</strong>.
            Each card embeds the post from the agency&rsquo;s own account, so
            attribution stays intact and a video removed upstream disappears here
            too instead of lingering as a stale copy.
          </li>
          <li>
            Nothing loads from Instagram until you press{" "}
            <strong className="font-semibold text-ink">Load video</strong>. This app
            renders children&rsquo;s records, and an embed that fired on page load
            would send a referrer from a clinical application to a third party on
            every visit.
          </li>
          <li>
            Demo content. Before this is used for real training, the videos need
            an owner, a review date, and a record of who has watched what &mdash;
            none of which this page tracks.
          </li>
        </ul>
      </Card>
    </div>
  );
}
