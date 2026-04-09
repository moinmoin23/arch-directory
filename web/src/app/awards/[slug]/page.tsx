import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getAwardBySlug } from "@/lib/queries/awards";
import { createServerClient } from "@/lib/supabase-server";

export const revalidate = 3600;

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const award = await getAwardBySlug(slug);
  if (!award) return {};

  const description = `${award.award_name} — ${award.organization || "Award details"}.`;

  return {
    title: `${award.award_name}${award.year ? ` (${award.year})` : ""}`,
    description,
    openGraph: {
      title: `${award.award_name}${award.year ? ` (${award.year})` : ""}`,
      description,
      url: `${BASE_URL}/awards/${slug}`,
    },
  };
}

export async function generateStaticParams() {
  const supabase = createServerClient();
  const { data } = await supabase.from("awards").select("slug");
  return (data ?? []).map((a) => ({ slug: a.slug }));
}

export default async function AwardDetailPage({ params }: Props) {
  const { slug } = await params;
  const award = await getAwardBySlug(slug);

  if (!award) notFound();

  // Schema.org JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: award.award_name,
    ...(award.organization && {
      creator: { "@type": "Organization", name: award.organization },
    }),
    ...(award.year && { dateCreated: String(award.year) }),
    ...(award.category && { genre: award.category }),
  };

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Awards",
        item: `${BASE_URL}/awards`,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: award.award_name,
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
      />
    <div className="mx-auto max-w-4xl px-6 py-12">
      {/* Breadcrumb */}
      <nav className="text-sm text-muted mb-8">
        <Link href="/awards" className="hover:text-foreground">
          Awards
        </Link>
        {" / "}
        <span className="text-foreground">{award.award_name}</span>
      </nav>

      {/* Header */}
      <h1 className="text-3xl font-bold tracking-tight">
        {award.award_name}
      </h1>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted">
        {award.organization && <span>{award.organization}</span>}
        {award.year && <span>{award.year}</span>}
        {award.category && <span>{award.category}</span>}
        <span className="border border-border px-2 py-0.5">
          Tier {award.prestige}
        </span>
      </div>

      {/* Recipients */}
      {award.award_recipients && award.award_recipients.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xl font-semibold mb-4">Recipients</h2>
          <div className="space-y-3">
            {award.award_recipients.map((ar, i) => {
              const firm = ar.firms;
              const person = ar.people;
              const firmSectorPath =
                firm && firm.sector === "multidisciplinary"
                  ? "technology"
                  : firm?.sector;

              return (
                <div
                  key={i}
                  className="flex items-baseline gap-3 border border-border p-4"
                >
                  {ar.year && (
                    <span className="text-sm font-medium">{ar.year}</span>
                  )}
                  <div>
                    {firm && (
                      <Link
                        href={`/${firmSectorPath}/firms/${firm.slug}`}
                        className="font-medium hover:underline"
                      >
                        {firm.display_name}
                      </Link>
                    )}
                    {person && (
                      <Link
                        href={`/people/${person.slug}`}
                        className="font-medium hover:underline"
                      >
                        {firm ? ` — ${person.display_name}` : person.display_name}
                      </Link>
                    )}
                    {ar.project_name && (
                      <p className="text-sm text-muted">{ar.project_name}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
    </>
  );
}
