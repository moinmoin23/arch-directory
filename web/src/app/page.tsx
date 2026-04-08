import Link from "next/link";
import { countFirmsBySector } from "@/lib/queries/firms";
import { createServerClient } from "@/lib/supabase-server";

const SECTORS = [
  {
    slug: "architecture",
    title: "Architecture",
    description:
      "Firms and practices shaping the built environment — from emerging studios to Pritzker-winning offices.",
  },
  {
    slug: "design",
    title: "Design",
    description:
      "Studios working across identity, product, interaction, and spatial design.",
  },
  {
    slug: "technology",
    title: "Technology",
    description:
      "Labs, fab labs, and companies advancing computational design, digital fabrication, and building tech.",
  },
] as const;

async function getStats() {
  const supabase = createServerClient();
  const [firmCounts, { count: peopleCount }, { count: awardsCount }, { count: sourceCount }] =
    await Promise.all([
      countFirmsBySector(),
      supabase
        .from("people")
        .select("*", { count: "exact", head: true })
        .eq("publish_status", "published"),
      supabase
        .from("awards")
        .select("*", { count: "exact", head: true }),
      supabase
        .from("sources")
        .select("*", { count: "exact", head: true }),
    ]);

  const totalFirms = Object.values(firmCounts).reduce((a, b) => a + b, 0);
  return {
    firmCounts,
    totalFirms,
    peopleCount: peopleCount ?? 0,
    awardsCount: awardsCount ?? 0,
    sourceCount: sourceCount ?? 0,
  };
}

export default async function HomePage() {
  const { firmCounts, totalFirms, peopleCount, awardsCount, sourceCount } =
    await getStats();

  return (
    <div className="mx-auto max-w-6xl px-6">
      {/* Hero */}
      <section className="py-20">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          A trusted, searchable map of the people,
          <br />
          firms, and technologies shaping
          <br />
          the built world.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-muted">
          TektonGraph connects architecture, design, and technology — from
          computational design researchers and digital fabrication labs to
          award-winning practices and the tools they build.
        </p>
        <div className="mt-8 flex gap-3">
          <Link
            href="/search"
            className="border border-foreground bg-foreground px-5 py-2.5 text-sm text-background transition-colors hover:bg-transparent hover:text-foreground"
          >
            Search the directory
          </Link>
          <Link
            href="/firms/country"
            className="border border-border px-5 py-2.5 text-sm transition-colors hover:border-foreground"
          >
            Browse by country
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 gap-8 border-y border-border py-8 sm:grid-cols-4">
        <div>
          <p className="text-3xl font-semibold">
            {totalFirms.toLocaleString()}
          </p>
          <p className="text-sm text-muted">Firms &amp; Labs</p>
        </div>
        <div>
          <p className="text-3xl font-semibold">
            {peopleCount.toLocaleString()}
          </p>
          <p className="text-sm text-muted">People</p>
        </div>
        <div>
          <p className="text-3xl font-semibold">{awardsCount}</p>
          <p className="text-sm text-muted">Awards</p>
        </div>
        <div>
          <p className="text-3xl font-semibold">
            {sourceCount.toLocaleString()}
          </p>
          <p className="text-sm text-muted">Sources</p>
        </div>
      </section>

      {/* Sector cards */}
      <section className="py-16">
        <h2 className="text-xl font-semibold mb-8">Browse by sector</h2>
        <div className="grid gap-6 sm:grid-cols-3">
          {SECTORS.map((sector) => (
            <Link
              key={sector.slug}
              href={`/${sector.slug}`}
              className="group block border border-border p-6 transition-colors hover:border-foreground"
            >
              <h3 className="text-lg font-semibold group-hover:underline">
                {sector.title}
              </h3>
              <p className="mt-2 text-sm text-muted">{sector.description}</p>
              <p className="mt-4 text-2xl font-semibold">
                {firmCounts[sector.slug] ?? 0}
              </p>
              <p className="text-xs text-muted">entities</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Quick links */}
      <section className="border-t border-border py-12">
        <h2 className="text-xl font-semibold mb-6">Explore</h2>
        <div className="flex flex-wrap gap-3">
          {[
            { href: "/people", label: "All People" },
            { href: "/people/role", label: "People by Role" },
            { href: "/firms/country", label: "Firms by Country" },
            { href: "/awards", label: "Awards" },
            { href: "/technology", label: "Technology Labs" },
            { href: "/sources", label: "Sources & Publications" },
          ].map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="border border-border px-4 py-2 text-sm transition-colors hover:border-foreground hover:bg-foreground hover:text-background"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
