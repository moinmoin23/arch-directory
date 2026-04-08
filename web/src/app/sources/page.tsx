import type { Metadata } from "next";
import { listSources } from "@/lib/queries/sources";
import { SourceList } from "@/components/SourceList";
import { Pagination } from "@/components/Pagination";
import { SearchBar } from "@/components/SearchBar";

const PER_PAGE = 36;

export const metadata: Metadata = {
  title: "Sources & Publications",
  description:
    "Articles, publications, and press coverage tracked by the Arch Directory.",
};

export default async function SourcesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;

  const { sources, count } = await listSources({ page, perPage: PER_PAGE });
  const totalPages = Math.ceil(count / PER_PAGE);

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">
        Sources &amp; Publications
      </h1>
      <p className="mt-2 text-muted">
        {count.toLocaleString()} sources tracked.
      </p>

      <SearchBar placeholder="Search sources..." className="mt-6" />

      <SourceList sources={sources} />

      {sources.length === 0 && (
        <p className="mt-8 text-muted">No sources yet.</p>
      )}

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        buildHref={(pg) => (pg <= 1 ? "/sources" : `/sources?page=${pg}`)}
        totalResults={count}
        perPage={PER_PAGE}
      />
    </div>
  );
}
