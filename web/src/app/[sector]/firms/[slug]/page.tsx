import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { getFirmBySlug, getFirmAliases, getFirmAwards, getFirmSources } from "@/lib/queries/firms";
import { SourceList } from "@/components/SourceList";
import { createServerClient } from "@/lib/supabase-server";

export const revalidate = 3600;

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

type Props = {
  params: Promise<{ sector: string; slug: string }>;
};

type FirmTagRow = {
  tags: {
    name: string;
    slug: string;
  } | null;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const firm = await getFirmBySlug(slug);
  if (!firm) return {};

  const location = [firm.city, firm.country].filter(Boolean).join(", ");
  const description =
    firm.short_description ||
    `${firm.display_name} is a ${firm.sector} firm${location ? ` based in ${location}` : ""}.`;
  const sectorPath = firm.sector === "multidisciplinary" ? "technology" : firm.sector;

  return {
    title: firm.display_name,
    description,
    openGraph: {
      title: firm.display_name,
      description,
      url: `${BASE_URL}/${sectorPath}/firms/${slug}`,
      type: "profile",
    },
    ...((isThinPage(firm) || firm.publish_status !== "published") && {
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
    .eq("publish_status", "published")
    .is("merged_into", null);

  return (data ?? []).map((firm) => ({
    sector: firm.sector === "multidisciplinary" ? "technology" : firm.sector,
    slug: firm.slug,
  }));
}

export default async function FirmDetailPage({ params }: Props) {
  const { slug } = await params;
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

  const supabase2 = createServerClient();
  const [aliases, awards, sources, tagsResult] = await Promise.all([
    getFirmAliases(firm.id),
    getFirmAwards(firm.id),
    getFirmSources(firm.id),
    supabase2
      .from("entity_tags")
      .select("tags(name, slug)")
      .eq("entity_id", firm.id)
      .eq("entity_type", "firm")
      .limit(10),
  ]);
  const tags = ((tagsResult.data ?? []) as FirmTagRow[])
    .map((et) => (et.tags ? { name: et.tags.name, slug: et.tags.slug } : null))
    .filter((t): t is { name: string; slug: string } => t !== null);

  const location = [firm.city, firm.country].filter(Boolean).join(", ");
  const sectorPath = firm.sector === "multidisciplinary" ? "technology" : firm.sector;

  // Schema.org JSON-LD — Organization
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: firm.display_name,
    ...(aliases.length > 0 && { alternateName: aliases }),
    ...(firm.website && { url: firm.website, sameAs: [firm.website] }),
    ...(firm.short_description && { description: firm.short_description }),
    ...(location && {
      address: {
        "@type": "PostalAddress",
        ...(firm.city && { addressLocality: firm.city }),
        ...(firm.country && { addressCountry: firm.country }),
      },
    }),
    ...(firm.founded_year && { foundingDate: String(firm.founded_year) }),
    ...(firm.firm_people &&
      firm.firm_people.length > 0 && {
        member: firm.firm_people.map((fp) => ({
          "@type": "Person",
          name: fp.people.display_name,
          ...(fp.role && { jobTitle: fp.role }),
        })),
      }),
    ...(awards.length > 0 && {
      award: awards.map((ar) => {
        const a = ar.awards as unknown as { award_name: string };
        return a.award_name;
      }),
    }),
    knowsAbout: firm.sector,
  };

  // Schema.org JSON-LD — BreadcrumbList
  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: firm.sector,
        item: `${BASE_URL}/${sectorPath}`,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Firms",
        item: `${BASE_URL}/${sectorPath}/firms`,
      },
      {
        "@type": "ListItem",
        position: 3,
        name: firm.display_name,
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

      {/* Hero image */}
      {firm.image_url && (
        <div className="w-full">
          <div className="aspect-[21/9] bg-muted/10 overflow-hidden">
            <img
              src={firm.image_url}
              alt={firm.display_name}
              className="h-full w-full object-cover"
            />
          </div>
          {firm.image_credit && (
            <p className="px-6 py-1 text-xs text-muted text-right">
              Photo: {firm.image_credit}
            </p>
          )}
        </div>
      )}

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

        {/* Tags */}
        {tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {tags.map((tag) => (
              <Link
                key={tag.slug}
                href={`/tags/${tag.slug}`}
                className="border border-border px-2 py-0.5 text-xs text-muted hover:border-foreground hover:text-foreground transition-colors"
              >
                {tag.name}
              </Link>
            ))}
          </div>
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

        {/* Sources & References */}
        <SourceList sources={sources} />
      </div>
    </>
  );
}
