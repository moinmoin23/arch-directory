import type { Metadata } from "next";
import Link from "next/link";
import { listAwards } from "@/lib/queries/awards";

export const metadata: Metadata = {
  title: "Awards",
  description:
    "Major architecture, design, and technology awards — Pritzker, RIBA, WAF, and more.",
};

export default async function AwardsPage() {
  const { awards, count } = await listAwards();

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Awards</h1>
      <p className="mt-2 text-muted">
        {count} awards tracked in the directory.
      </p>

      <section className="mt-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {awards.map((award) => (
            <Link
              key={award.id}
              href={`/awards/${award.slug}`}
              className="group block border border-border p-5 transition-colors hover:border-foreground"
            >
              <h3 className="font-semibold group-hover:underline">
                {award.award_name}
              </h3>
              <p className="mt-1 text-sm text-muted">
                {award.organization}
                {award.year ? ` · ${award.year}` : ""}
              </p>
              {award.category && (
                <p className="mt-2 text-sm text-muted">{award.category}</p>
              )}
              <div className="mt-3">
                <span className="inline-block border border-border px-2 py-0.5 text-xs text-muted">
                  Tier {award.prestige}
                </span>
              </div>
            </Link>
          ))}
        </div>
        {awards.length === 0 && (
          <p className="text-muted">No awards found.</p>
        )}
      </section>
    </div>
  );
}
