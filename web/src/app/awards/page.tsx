import type { Metadata } from "next";
import Link from "next/link";
import { listAwards, getOrganizationsWithCounts } from "@/lib/queries/awards";
import { Pagination } from "@/components/Pagination";
import { SearchBar } from "@/components/SearchBar";
import { FilterChips } from "@/components/FilterChips";

const PER_PAGE = 36;

export const metadata: Metadata = {
  title: "Awards",
  description:
    "Major architecture, design, and technology awards — Pritzker, RIBA, WAF, and more.",
};

export default async function AwardsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; org?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  const org = params.org || undefined;

  const [{ awards, count }, organizations] = await Promise.all([
    listAwards({ page, perPage: PER_PAGE, organization: org }),
    getOrganizationsWithCounts(),
  ]);

  const totalPages = Math.ceil(count / PER_PAGE);

  const filters: { label: string; removeHref: string }[] = [];
  if (org) {
    filters.push({ label: org, removeHref: "/awards" });
  }

  function buildHref(pg: number) {
    const p = new URLSearchParams();
    if (pg > 1) p.set("page", String(pg));
    if (org) p.set("org", org);
    const qs = p.toString();
    return `/awards${qs ? `?${qs}` : ""}`;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Awards</h1>
      <p className="mt-2 text-muted">
        {count.toLocaleString()} awards tracked in the directory.
      </p>

      <SearchBar placeholder="Search awards..." className="mt-6" />

      {/* Organization filter */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted">Organization</span>
        <Link
          href="/awards"
          className={`border px-2.5 py-1 text-xs transition-colors ${
            !org
              ? "border-foreground bg-foreground text-background"
              : "border-border hover:border-foreground"
          }`}
        >
          All
        </Link>
        {organizations.map((o) => (
          <Link
            key={o.organization}
            href={`/awards?org=${encodeURIComponent(o.organization)}`}
            className={`border px-2.5 py-1 text-xs transition-colors ${
              org === o.organization
                ? "border-foreground bg-foreground text-background"
                : "border-border hover:border-foreground"
            }`}
          >
            {o.organization} ({o.count})
          </Link>
        ))}
      </div>

      {filters.length > 0 && (
        <div className="mt-3">
          <FilterChips filters={filters} clearAllHref="/awards" />
        </div>
      )}

      <section className="mt-8">
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
          <div className="py-12 text-center">
            <p className="text-muted">No awards found matching your filters.</p>
            <Link
              href="/awards"
              className="mt-2 inline-block text-sm underline hover:text-foreground"
            >
              Clear all filters
            </Link>
          </div>
        )}
      </section>

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        buildHref={buildHref}
        totalResults={count}
        perPage={PER_PAGE}
      />
    </div>
  );
}
