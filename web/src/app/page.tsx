import Link from "next/link";
import { countFirmsBySector } from "@/lib/queries/firms";
import { createServerClient } from "@/lib/supabase-server";

const SECTORS = [
  {
    slug: "architecture",
    title: "Architecture",
    description:
      "Firms shaping the built environment — from residential to urban-scale projects.",
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
      "Labs and companies advancing computational design, fabrication, and building tech.",
  },
] as const;

async function getStats() {
  const supabase = createServerClient();
  const [firmCounts, { count: peopleCount }, { count: awardsCount }] =
    await Promise.all([
      countFirmsBySector(),
      supabase
        .from("people")
        .select("*", { count: "exact", head: true }),
      supabase
        .from("awards")
        .select("*", { count: "exact", head: true }),
    ]);

  const totalFirms = Object.values(firmCounts).reduce((a, b) => a + b, 0);
  return { firmCounts, totalFirms, peopleCount: peopleCount ?? 0, awardsCount: awardsCount ?? 0 };
}

export default async function HomePage() {
  const { firmCounts, totalFirms, peopleCount, awardsCount } = await getStats();

  return (
    <div className="mx-auto max-w-6xl px-6">
      {/* Hero */}
      <section className="py-20">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          The global directory of architecture,
          <br />
          design &amp; technology
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted">
          A structured, source-backed reference covering firms, studios, labs,
          and the people behind them.
        </p>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-3 gap-8 border-y border-border py-8">
        <div>
          <p className="text-3xl font-semibold">{totalFirms}</p>
          <p className="text-sm text-muted">Firms &amp; Studios</p>
        </div>
        <div>
          <p className="text-3xl font-semibold">{peopleCount}</p>
          <p className="text-sm text-muted">People</p>
        </div>
        <div>
          <p className="text-3xl font-semibold">{awardsCount}</p>
          <p className="text-sm text-muted">Awards</p>
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
            { href: "/awards", label: "Awards" },
            { href: "/architecture?country=Netherlands", label: "Firms in Netherlands" },
            { href: "/architecture?country=United+Kingdom", label: "Firms in UK" },
            { href: "/technology", label: "Technology Labs" },
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
