import type { Metadata } from "next";
import Link from "next/link";
import { listPeople, getPeopleLetterCounts } from "@/lib/queries/people";
import { PersonCard } from "@/components/PersonCard";
import { Pagination } from "@/components/Pagination";
import { AlphabetNav } from "@/components/AlphabetNav";
import { FilterChips } from "@/components/FilterChips";
import { SearchBar } from "@/components/SearchBar";
import type { Enums } from "@/lib/database.types";

const VALID_SECTORS = ["architecture", "design", "technology", "multidisciplinary"] as const;

const PER_PAGE = 36;

export const metadata: Metadata = {
  title: "People",
  description:
    "Architects, designers, researchers, and technologists shaping the built environment.",
};

const SORT_OPTIONS = [
  { value: "name", label: "A–Z" },
  { value: "recent", label: "Recently added" },
] as const;

const SECTOR_OPTIONS = [
  { value: "", label: "All sectors" },
  { value: "architecture", label: "Architecture" },
  { value: "design", label: "Design" },
  { value: "technology", label: "Technology" },
] as const;

export default async function PeoplePage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string;
    letter?: string;
    sector?: string;
    sort?: string;
  }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  const letter = params.letter?.toUpperCase() || undefined;
  const sectorParam = params.sector || "";
  const sector = VALID_SECTORS.includes(sectorParam as Enums<"sector_type">)
    ? (sectorParam as Enums<"sector_type">)
    : undefined;
  const sort = params.sort === "recent" ? "recent" : "name";

  const [{ people, count }, availableLetters] = await Promise.all([
    listPeople({ page, perPage: PER_PAGE, letter, sector, sort }),
    getPeopleLetterCounts(),
  ]);

  const totalPages = Math.ceil(count / PER_PAGE);

  // Build active filter chips
  const filters: { label: string; removeHref: string }[] = [];
  if (letter) {
    const p = new URLSearchParams();
    if (sector) p.set("sector", sector);
    if (sort !== "name") p.set("sort", sort);
    const qs = p.toString();
    filters.push({
      label: `Letter: ${letter}`,
      removeHref: `/people${qs ? `?${qs}` : ""}`,
    });
  }
  if (sector) {
    const p = new URLSearchParams();
    if (letter) p.set("letter", letter);
    if (sort !== "name") p.set("sort", sort);
    const qs = p.toString();
    filters.push({
      label: `Sector: ${sector}`,
      removeHref: `/people${qs ? `?${qs}` : ""}`,
    });
  }

  function buildHref(pg: number) {
    const p = new URLSearchParams();
    if (pg > 1) p.set("page", String(pg));
    if (letter) p.set("letter", letter);
    if (sector) p.set("sector", sector);
    if (sort !== "name") p.set("sort", sort);
    const qs = p.toString();
    return `/people${qs ? `?${qs}` : ""}`;
  }

  function buildSortHref(s: string) {
    const p = new URLSearchParams();
    if (letter) p.set("letter", letter);
    if (sector) p.set("sector", sector);
    if (s !== "name") p.set("sort", s);
    const qs = p.toString();
    return `/people${qs ? `?${qs}` : ""}`;
  }

  function buildSectorHref(s: string) {
    const p = new URLSearchParams();
    if (letter) p.set("letter", letter);
    if (sort !== "name") p.set("sort", sort);
    if (s) p.set("sector", s);
    const qs = p.toString();
    return `/people${qs ? `?${qs}` : ""}`;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">People</h1>
      <p className="mt-2 text-muted">
        {count.toLocaleString()} people in the directory.
      </p>

      <SearchBar placeholder="Search people..." className="mt-6" />

      {/* Alphabet navigation */}
      <div className="mt-6">
        <AlphabetNav
          activeLetter={letter ?? null}
          basePath="/people"
          availableLetters={availableLetters}
          extraParams={{
            ...(sector ? { sector } : {}),
            ...(sort !== "name" ? { sort } : {}),
          }}
        />
      </div>

      {/* Filter bar */}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label htmlFor="sector-filter" className="text-xs text-muted">
            Sector
          </label>
          {SECTOR_OPTIONS.map((opt) => (
            <Link
              key={opt.value}
              href={buildSectorHref(opt.value)}
              className={`border px-2.5 py-1 text-xs transition-colors ${
                (sector || "") === opt.value
                  ? "border-foreground bg-foreground text-background"
                  : "border-border hover:border-foreground"
              }`}
            >
              {opt.label}
            </Link>
          ))}
        </div>

        <span className="text-border">|</span>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Sort</span>
          {SORT_OPTIONS.map((opt) => (
            <Link
              key={opt.value}
              href={buildSortHref(opt.value)}
              className={`border px-2.5 py-1 text-xs transition-colors ${
                sort === opt.value
                  ? "border-foreground bg-foreground text-background"
                  : "border-border hover:border-foreground"
              }`}
            >
              {opt.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Active filter chips */}
      {filters.length > 0 && (
        <div className="mt-3">
          <FilterChips filters={filters} clearAllHref="/people" />
        </div>
      )}

      {/* Results grid */}
      <section className="mt-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {people.map((person) => (
            <PersonCard key={person.id} person={person} />
          ))}
        </div>
        {people.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-muted">
              No people found matching your filters.
            </p>
            <Link
              href="/people"
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
