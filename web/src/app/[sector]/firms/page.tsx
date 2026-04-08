import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { listFirmsBySector, listFirmsBySectorAndCountry } from "@/lib/queries/firms";
import { FirmCard } from "@/components/FirmCard";
import { Pagination } from "@/components/Pagination";
import { FilterChips } from "@/components/FilterChips";
import type { Enums } from "@/lib/database.types";

const VALID_SECTORS = ["architecture", "design", "technology"] as const;
type Sector = (typeof VALID_SECTORS)[number];

const SECTOR_LABELS: Record<Sector, string> = {
  architecture: "Architecture Firms",
  design: "Design Studios",
  technology: "Technology Labs",
};

const PER_PAGE = 36;

type Props = {
  params: Promise<{ sector: string }>;
  searchParams: Promise<{ page?: string; country?: string; sort?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { sector } = await params;
  if (!VALID_SECTORS.includes(sector as Sector)) return {};

  const label = SECTOR_LABELS[sector as Sector];
  return {
    title: label,
    description: `Browse ${label.toLowerCase()} in the Arch Directory.`,
  };
}

export default async function SectorFirmsPage({ params, searchParams }: Props) {
  const { sector } = await params;
  const sp = await searchParams;

  if (!VALID_SECTORS.includes(sector as Sector)) notFound();

  const page = Number(sp.page) || 1;
  const country = sp.country;

  const { firms, count } = country
    ? await listFirmsBySectorAndCountry(
        sector as Enums<"sector_type">,
        country,
        { page, perPage: PER_PAGE }
      )
    : await listFirmsBySector(sector as Enums<"sector_type">, {
        page,
        perPage: PER_PAGE,
      });

  const label = SECTOR_LABELS[sector as Sector];
  const totalPages = Math.ceil(count / PER_PAGE);

  // Active filter chips
  const filters: { label: string; removeHref: string }[] = [];
  if (country) {
    filters.push({
      label: `Country: ${country}`,
      removeHref: `/${sector}/firms`,
    });
  }

  function buildHref(pg: number) {
    const p = new URLSearchParams();
    if (pg > 1) p.set("page", String(pg));
    if (country) p.set("country", country);
    const qs = p.toString();
    return `/${sector}/firms${qs ? `?${qs}` : ""}`;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">{label}</h1>
      <p className="mt-2 text-muted">
        {count.toLocaleString()} results
      </p>

      {/* Country filter */}
      <div className="mt-4">
        <form
          action={`/${sector}/firms`}
          method="GET"
          className="flex items-center gap-3"
        >
          <label htmlFor="country-filter" className="text-xs text-muted">
            Country
          </label>
          <input
            id="country-filter"
            type="text"
            name="country"
            defaultValue={country || ""}
            placeholder="e.g. US, DE, JP"
            className="border border-border bg-transparent px-3 py-1.5 text-sm placeholder:text-muted/60 focus:border-foreground focus:outline-none"
          />
          <button
            type="submit"
            className="border border-border px-3 py-1.5 text-xs transition-colors hover:border-foreground"
          >
            Filter
          </button>
        </form>
      </div>

      {/* Active filter chips */}
      {filters.length > 0 && (
        <div className="mt-3">
          <FilterChips filters={filters} clearAllHref={`/${sector}/firms`} />
        </div>
      )}

      {/* Results grid */}
      <section className="mt-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {firms.map((firm) => (
            <FirmCard key={firm.id} firm={firm} />
          ))}
        </div>
        {firms.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-muted">
              No firms found matching your filters.
            </p>
            <Link
              href={`/${sector}/firms`}
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
