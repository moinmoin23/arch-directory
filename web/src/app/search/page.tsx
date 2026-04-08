import type { Metadata } from "next";
import Link from "next/link";
import { searchDirectory, type SearchResult } from "@/lib/queries/search";

export const metadata: Metadata = {
  title: "Search",
  description:
    "Search architecture firms, design studios, technology labs, and people in the directory.",
};

function FirmResult({ result }: { result: SearchResult }) {
  const sectorPath =
    result.sector === "multidisciplinary" ? "technology" : result.sector;
  return (
    <Link
      href={`/${sectorPath}/firms/${result.slug}`}
      className="group block border border-border p-5 transition-colors hover:border-foreground"
    >
      <h3 className="font-semibold group-hover:underline">
        {result.display_name}
      </h3>
      <p className="mt-1 text-sm text-muted">
        {[result.city, result.country].filter(Boolean).join(", ")}
      </p>
      {result.short_description && (
        <p className="mt-2 text-sm text-muted line-clamp-2">
          {result.short_description}
        </p>
      )}
      <div className="mt-3">
        <span className="inline-block border border-border px-2 py-0.5 text-xs text-muted">
          {result.sector}
        </span>
      </div>
    </Link>
  );
}

function PersonResult({ result }: { result: SearchResult }) {
  return (
    <Link
      href={`/people/${result.slug}`}
      className="group block border border-border p-5 transition-colors hover:border-foreground"
    >
      <h3 className="font-semibold group-hover:underline">
        {result.display_name}
      </h3>
      <p className="mt-1 text-sm text-muted">{result.role}</p>
      {result.short_description && (
        <p className="mt-2 text-sm text-muted line-clamp-2">
          {result.short_description}
        </p>
      )}
      <div className="mt-3">
        <span className="inline-block border border-border px-2 py-0.5 text-xs text-muted">
          {result.sector}
        </span>
      </div>
    </Link>
  );
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; sector?: string; country?: string }>;
}) {
  const params = await searchParams;
  const query = params.q || "";
  const sector = params.sector;
  const country = params.country;

  const { firms, people } = query
    ? await searchDirectory(query, { sector, country })
    : { firms: [], people: [] };

  const totalResults = firms.length + people.length;

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Search</h1>
      <p className="mt-2 text-muted">
        Find firms, labs, studios, and people across architecture, design, and
        technology.
      </p>

      <form action="/search" method="GET" className="mt-8">
        <div className="flex gap-3">
          <input
            type="text"
            name="q"
            defaultValue={query}
            placeholder="Search by name, description, location..."
            className="flex-1 border border-border bg-transparent px-4 py-2.5 text-sm placeholder:text-muted focus:border-foreground focus:outline-none"
          />
          <button
            type="submit"
            className="border border-foreground bg-foreground px-6 py-2.5 text-sm text-background transition-colors hover:bg-transparent hover:text-foreground"
          >
            Search
          </button>
        </div>

        <div className="mt-3 flex gap-3">
          <select
            name="sector"
            defaultValue={sector || ""}
            className="border border-border bg-transparent px-3 py-1.5 text-sm text-muted"
          >
            <option value="">All sectors</option>
            <option value="architecture">Architecture</option>
            <option value="design">Design</option>
            <option value="technology">Technology</option>
          </select>
          <input
            type="text"
            name="country"
            defaultValue={country || ""}
            placeholder="Country code (e.g. US, DE)"
            className="border border-border bg-transparent px-3 py-1.5 text-sm placeholder:text-muted"
          />
        </div>
      </form>

      {query && (
        <p className="mt-8 text-sm text-muted">
          {totalResults} result{totalResults !== 1 ? "s" : ""} for &ldquo;
          {query}&rdquo;
          {sector ? ` in ${sector}` : ""}
          {country ? ` (${country})` : ""}
        </p>
      )}

      {firms.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">
            Firms & Labs ({firms.length})
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {firms.map((r) => (
              <FirmResult key={r.id} result={r} />
            ))}
          </div>
        </section>
      )}

      {people.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">People ({people.length})</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {people.map((r) => (
              <PersonResult key={r.id} result={r} />
            ))}
          </div>
        </section>
      )}

      {query && totalResults === 0 && (
        <div className="mt-12 text-center">
          <p className="text-muted">
            No results found. Try a different search term or broaden your
            filters.
          </p>
        </div>
      )}

      {!query && (
        <div className="mt-12 text-center">
          <p className="text-muted">
            Enter a search term above to find firms, labs, studios, and people.
          </p>
        </div>
      )}
    </div>
  );
}
