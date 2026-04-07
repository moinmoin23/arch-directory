import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { getFirmBySlug, getFirmAliases, getFirmAwards } from "@/lib/queries/firms";
import { createServerClient } from "@/lib/supabase-server";

type Props = {
  params: Promise<{ sector: string; slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const firm = await getFirmBySlug(slug);
  if (!firm) return {};

  const location = [firm.city, firm.country].filter(Boolean).join(", ");
  return {
    title: firm.display_name,
    description:
      firm.short_description ||
      `${firm.display_name} is a ${firm.sector} firm${location ? ` based in ${location}` : ""}.`,
    ...(isThinPage(firm) && {
      robots: { index: false, follow: true },
    }),
  };
}

function isThinPage(firm: NonNullable<Awaited<ReturnType<typeof getFirmBySlug>>>) {
  let points = 0;
  if (firm.short_description) points++;
  if (firm.country) points++;
  if (firm.city) points++;
  if (firm.website) points++;
  if (firm.founded_year) points++;
  if (firm.firm_people?.length > 0) points++;
  return points < 3;
}

export async function generateStaticParams() {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("firms")
    .select("slug, sector")
    .is("merged_into", null);

  return (data ?? []).map((firm) => ({
    sector: firm.sector === "multidisciplinary" ? "technology" : firm.sector,
    slug: firm.slug,
  }));
}

export default async function FirmDetailPage({ params }: Props) {
  const { sector, slug } = await params;
  const firm = await getFirmBySlug(slug);

  if (!firm) notFound();

  // Redirect merged entities to their canonical record
  if (firm.merged_into) {
    const supabase = createServerClient();
    const { data: canonical } = await supabase
      .from("firms")
      .select("slug, sector")
      .eq("id", firm.merged_into)
      .single();

    if (canonical) {
      const canonicalSector =
        canonical.sector === "multidisciplinary" ? "technology" : canonical.sector;
      redirect(`/${canonicalSector}/firms/${canonical.slug}`);
    }
  }

  const [aliases, awards] = await Promise.all([
    getFirmAliases(firm.id),
    getFirmAwards(firm.id),
  ]);

  const location = [firm.city, firm.country].filter(Boolean).join(", ");
  const sectorPath = firm.sector === "multidisciplinary" ? "technology" : firm.sector;

  // Schema.org JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: firm.display_name,
    ...(aliases.length > 0 && { alternateName: aliases }),
    ...(firm.website && { url: firm.website }),
    ...(firm.short_description && { description: firm.short_description }),
    ...(location && {
      address: {
        "@type": "PostalAddress",
        ...(firm.city && { addressLocality: firm.city }),
        ...(firm.country && { addressCountry: firm.country }),
      },
    }),
    ...(firm.founded_year && { foundingDate: String(firm.founded_year) }),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="mx-auto max-w-4xl px-6 py-12">
        {/* Breadcrumb */}
        <nav className="text-sm text-muted mb-8">
          <Link href={`/${sectorPath}`} className="hover:text-foreground">
            {firm.sector}
          </Link>
          {" / "}
          <Link
            href={`/${sectorPath}/firms`}
            className="hover:text-foreground"
          >
            Firms
          </Link>
          {" / "}
          <span className="text-foreground">{firm.display_name}</span>
        </nav>

        {/* Header */}
        <h1 className="text-3xl font-bold tracking-tight">
          {firm.display_name}
        </h1>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted">
          <span className="border border-border px-2 py-0.5">{firm.sector}</span>
          {location && <span>{location}</span>}
          {firm.founded_year && <span>Est. {firm.founded_year}</span>}
          {firm.size_range && <span>{firm.size_range} people</span>}
        </div>

        {aliases.length > 0 && (
          <p className="mt-3 text-sm text-muted">
            Also known as: {aliases.join(", ")}
          </p>
        )}

        {/* Description */}
        {firm.short_description && (
          <section className="mt-8">
            <p className="text-base leading-relaxed">
              {firm.short_description}
            </p>
          </section>
        )}

        {/* Website */}
        {firm.website && (
          <section className="mt-6">
            <a
              href={firm.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted underline hover:text-foreground"
            >
              {firm.website.replace(/^https?:\/\//, "")}
            </a>
          </section>
        )}

        {/* Key People */}
        {firm.firm_people && firm.firm_people.length > 0 && (
          <section className="mt-10">
            <h2 className="text-xl font-semibold mb-4">Key People</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {firm.firm_people.map((fp) => (
                <Link
                  key={fp.people.id}
                  href={`/people/${fp.people.slug}`}
                  className="group block border border-border p-4 transition-colors hover:border-foreground"
                >
                  <p className="font-medium group-hover:underline">
                    {fp.people.display_name}
                  </p>
                  {fp.role && (
                    <p className="text-sm text-muted">{fp.role}</p>
                  )}
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Awards */}
        {awards.length > 0 && (
          <section className="mt-10">
            <h2 className="text-xl font-semibold mb-4">Awards</h2>
            <ul className="space-y-2">
              {awards.map((ar, i) => {
                const award = ar.awards as unknown as {
                  slug: string;
                  award_name: string;
                  organization: string | null;
                };
                return (
                  <li key={i} className="flex items-baseline gap-2">
                    <span className="text-sm text-muted">{ar.year}</span>
                    <Link
                      href={`/awards/${award.slug}`}
                      className="text-sm hover:underline"
                    >
                      {award.award_name}
                    </Link>
                    {award.organization && (
                      <span className="text-sm text-muted">
                        ({award.organization})
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </div>
    </>
  );
}
