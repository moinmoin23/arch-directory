import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getTagBySlug, getEntitiesForTag } from "@/lib/queries/tags";
import { FirmCard } from "@/components/FirmCard";
import { PersonCard } from "@/components/PersonCard";
import { createServerClient } from "@/lib/supabase-server";

export const revalidate = 3600;

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const tag = await getTagBySlug(slug);
  if (!tag) return {};

  return {
    title: tag.name,
    description: `Firms and people tagged "${tag.name}" on TektonGraph.`,
    openGraph: {
      title: tag.name,
      description: `Firms and people tagged "${tag.name}" on TektonGraph.`,
      url: `${BASE_URL}/tags/${slug}`,
    },
  };
}

export async function generateStaticParams() {
  const supabase = createServerClient();
  const { data } = await supabase.from("tags").select("slug");
  return (data ?? []).map((t) => ({ slug: t.slug }));
}

export default async function TagDetailPage({ params }: Props) {
  const { slug } = await params;
  const tag = await getTagBySlug(slug);

  if (!tag) notFound();

  const { firms, people } = await getEntitiesForTag(tag.id);

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Tags",
        item: `${BASE_URL}/tags`,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: tag.name,
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
      />

      <div className="mx-auto max-w-6xl px-6 py-12">
        {/* Breadcrumb */}
        <nav className="text-sm text-muted mb-8">
          <Link href="/tags" className="hover:text-foreground">
            Tags
          </Link>
          {" / "}
          <span className="text-foreground">{tag.name}</span>
        </nav>

        <h1 className="text-3xl font-bold tracking-tight">{tag.name}</h1>
        {tag.category && (
          <p className="mt-2 text-sm text-muted capitalize">{tag.category}</p>
        )}
        <p className="mt-2 text-muted">
          {firms.length + people.length} results
        </p>

        {/* Firms */}
        {firms.length > 0 && (
          <section className="mt-10">
            <h2 className="text-xl font-semibold mb-4">
              Firms ({firms.length})
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {firms.map((firm) => (
                <FirmCard key={firm.id} firm={firm} />
              ))}
            </div>
          </section>
        )}

        {/* People */}
        {people.length > 0 && (
          <section className="mt-10">
            <h2 className="text-xl font-semibold mb-4">
              People ({people.length})
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {people.map((person) => (
                <PersonCard key={person.id} person={person} />
              ))}
            </div>
          </section>
        )}

        {firms.length === 0 && people.length === 0 && (
          <p className="mt-12 text-center text-muted">
            No entities tagged with "{tag.name}" yet.
          </p>
        )}
      </div>
    </>
  );
}
