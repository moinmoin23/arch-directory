import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getPersonBySlug,
  getPersonAwards,
  getPersonAliases,
} from "@/lib/queries/people";
import { createServerClient } from "@/lib/supabase-server";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const person = await getPersonBySlug(slug);
  if (!person) return {};

  return {
    title: person.display_name,
    description:
      person.bio?.slice(0, 160) ||
      `${person.display_name} — ${person.role || person.sector}`,
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

  const [aliases, awards] = await Promise.all([
    getPersonAliases(person.id),
    getPersonAwards(person.id),
  ]);

  const firm = person.firms;
  const firmSectorPath =
    firm && firm.sector === "multidisciplinary" ? "technology" : firm?.sector;

  // Schema.org JSON-LD
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
          <Link href="/people" className="hover:text-foreground">
            People
          </Link>
          {" / "}
          <span className="text-foreground">{person.display_name}</span>
        </nav>

        {/* Header */}
        <h1 className="text-3xl font-bold tracking-tight">
          {person.display_name}
        </h1>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted">
          <span className="border border-border px-2 py-0.5">
            {person.sector}
          </span>
          {person.role && <span>{person.role}</span>}
          {person.nationality && <span>{person.nationality}</span>}
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

        {/* Bio */}
        {person.bio && (
          <section className="mt-8">
            <p className="text-base leading-relaxed">{person.bio}</p>
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
