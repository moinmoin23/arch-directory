import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getPersonBySlug,
  getPersonAwards,
  getPersonAliases,
  getPersonSources,
} from "@/lib/queries/people";
import { SourceList } from "@/components/SourceList";
import { createServerClient } from "@/lib/supabase-server";

export const revalidate = 3600;

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const person = await getPersonBySlug(slug);
  if (!person) return {};

  const description =
    person.bio?.slice(0, 160) ||
    `${person.display_name} — ${person.role || person.sector}`;

  return {
    title: person.display_name,
    description,
    openGraph: {
      title: person.display_name,
      description,
      url: `${BASE_URL}/people/${slug}`,
      type: "profile",
    },
  };
}

export async function generateStaticParams() {
  const supabase = createServerClient();
  const { data } = await supabase.from("people").select("slug");
  return (data ?? []).map((p) => ({ slug: p.slug }));
}

export default async function PersonDetailPage({ params }: Props) {
  const { slug } = await params;
  const person = await getPersonBySlug(slug);

  if (!person) notFound();

  const supabase = createServerClient();
  const [aliases, awards, sources, educationResult, tagsResult] = await Promise.all([
    getPersonAliases(person.id),
    getPersonAwards(person.id),
    getPersonSources(person.id),
    supabase
      .from("education")
      .select("institution_name, degree, field, start_year, end_year")
      .eq("person_id", person.id)
      .order("start_year", { ascending: false }),
    supabase
      .from("entity_tags")
      .select("tags(name, slug)")
      .eq("entity_id", person.id)
      .eq("entity_type", "person")
      .limit(10),
  ]);
  const education = educationResult.data ?? [];
  const tags = (tagsResult.data ?? [])
    .map((et: any) => et.tags ? { name: et.tags.name as string, slug: et.tags.slug as string } : null)
    .filter((t): t is { name: string; slug: string } => t !== null);

  const firm = person.firms;
  const firmSectorPath =
    firm && firm.sector === "multidisciplinary" ? "technology" : firm?.sector;

  // Schema.org JSON-LD — Person
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: person.display_name,
    ...(aliases.length > 0 && { alternateName: aliases }),
    ...(person.bio && { description: person.bio }),
    ...(person.role && { jobTitle: person.role }),
    ...(person.nationality && { nationality: person.nationality }),
    ...(firm && {
      worksFor: {
        "@type": "Organization",
        name: firm.display_name,
        ...(firm.website && { url: firm.website }),
      },
    }),
    ...(awards.length > 0 && {
      award: awards.map((ar) => {
        const a = ar.awards as unknown as { award_name: string };
        return a.award_name;
      }),
    }),
    knowsAbout: person.sector,
  };

  // Schema.org JSON-LD — BreadcrumbList
  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "People",
        item: `${BASE_URL}/people`,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: person.display_name,
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
          <Link href="/people" className="hover:text-foreground">
            People
          </Link>
          {" / "}
          <span className="text-foreground">{person.display_name}</span>
        </nav>

        {/* Header */}
        <div className="flex items-start gap-6">
          {person.image_url && (
            <div className="flex-shrink-0">
              <img
                src={person.image_url}
                alt={person.display_name}
                className="h-24 w-24 rounded-full object-cover"
              />
              {person.image_credit && (
                <p className="mt-1 text-[10px] text-muted text-center">
                  {person.image_credit}
                </p>
              )}
            </div>
          )}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {person.display_name}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted">
              <span className="border border-border px-2 py-0.5">
                {person.sector}
              </span>
              {person.role && <span>{person.role}</span>}
              {person.nationality && <span>{person.nationality}</span>}
              {person.birth_year && (
                <span>
                  b. {person.birth_year}
                  {person.death_year ? ` — d. ${person.death_year}` : ""}
                </span>
              )}
            </div>
          </div>
        </div>

        {aliases.length > 0 && (
          <p className="mt-3 text-sm text-muted">
            Also known as: {aliases.join(", ")}
          </p>
        )}

        {/* Firm association */}
        {firm && (
          <section className="mt-8 border border-border p-5">
            <p className="text-sm text-muted">Current firm</p>
            <Link
              href={`/${firmSectorPath}/firms/${firm.slug}`}
              className="text-lg font-semibold hover:underline"
            >
              {firm.display_name}
            </Link>
            {person.role && (
              <p className="text-sm text-muted">{person.role}</p>
            )}
          </section>
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

        {/* Bio */}
        {person.bio && (
          <section className="mt-8">
            <p className="text-base leading-relaxed">{person.bio}</p>
          </section>
        )}

        {/* Education */}
        {education.length > 0 && (
          <section className="mt-10">
            <h2 className="text-xl font-semibold mb-4">Education</h2>
            <ul className="space-y-2">
              {education.map((edu, i) => (
                <li key={i} className="flex items-baseline gap-2 text-sm">
                  {edu.start_year && (
                    <span className="text-muted">
                      {edu.start_year}
                      {edu.end_year ? `–${edu.end_year}` : ""}
                    </span>
                  )}
                  <span>{edu.institution_name}</span>
                  {edu.degree && (
                    <span className="text-muted">({edu.degree})</span>
                  )}
                  {edu.field && (
                    <span className="text-muted">— {edu.field}</span>
                  )}
                </li>
              ))}
            </ul>
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
