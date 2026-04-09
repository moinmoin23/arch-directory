import type { Metadata } from "next";
import Link from "next/link";
import { listFirmsBySector } from "@/lib/queries/firms";
import { listPeopleBySector } from "@/lib/queries/people";
import { FirmCard } from "@/components/FirmCard";
import { PersonCard } from "@/components/PersonCard";
import { Pagination } from "@/components/Pagination";
import { SearchBar } from "@/components/SearchBar";

export const revalidate = 1800;

const PER_PAGE = 36;

export const metadata: Metadata = {
  title: "Technology Labs & Research",
  description:
    "Browse technology labs, research groups, and companies advancing computational design, fabrication, and building tech.",
};

export default async function TechnologyPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;

  const [{ firms, count }, { people }] = await Promise.all([
    listFirmsBySector("technology", { page, perPage: PER_PAGE }),
    listPeopleBySector("technology", { perPage: 6 }),
  ]);

  const totalPages = Math.ceil(count / PER_PAGE);

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Technology</h1>
      <p className="mt-2 text-muted">
        {count.toLocaleString()} labs and research entities in the directory.
      </p>

      <SearchBar
        placeholder="Search technology labs and researchers..."
        sector="technology"
        className="mt-6"
      />

      <section className="mt-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Labs &amp; Companies</h2>
          <Link
            href="/technology/firms"
            className="text-sm text-muted hover:text-foreground"
          >
            View all →
          </Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {firms.map((firm) => (
            <FirmCard key={firm.id} firm={firm} />
          ))}
        </div>
        {firms.length === 0 && (
          <p className="text-muted">No entities found.</p>
        )}
      </section>

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        buildHref={(pg) => (pg <= 1 ? "/technology" : `/technology?page=${pg}`)}
        totalResults={count}
        perPage={PER_PAGE}
      />

      {people.length > 0 && (
        <section className="mt-16">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Notable People</h2>
            <Link
              href="/people?sector=technology"
              className="text-sm text-muted hover:text-foreground"
            >
              View all →
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {people.map((person) => (
              <PersonCard key={person.id} person={person} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
