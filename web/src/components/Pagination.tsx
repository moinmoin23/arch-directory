import Link from "next/link";

type Props = {
  currentPage: number;
  totalPages: number;
  buildHref: (page: number) => string;
  totalResults: number;
  perPage: number;
};

export function Pagination({
  currentPage,
  totalPages,
  buildHref,
  totalResults,
  perPage,
}: Props) {
  if (totalPages <= 1) return null;

  const from = (currentPage - 1) * perPage + 1;
  const to = Math.min(currentPage * perPage, totalResults);

  // Build a window of page numbers around the current page
  const pages: (number | "...")[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (currentPage > 3) pages.push("...");
    for (
      let i = Math.max(2, currentPage - 1);
      i <= Math.min(totalPages - 1, currentPage + 1);
      i++
    ) {
      pages.push(i);
    }
    if (currentPage < totalPages - 2) pages.push("...");
    pages.push(totalPages);
  }

  return (
    <nav
      className="mt-10 flex flex-col items-center gap-4"
      aria-label="Pagination"
    >
      <p className="text-sm text-muted">
        Showing {from}–{to} of {totalResults.toLocaleString()}
      </p>
      <div className="flex items-center gap-1">
        {currentPage > 1 ? (
          <Link
            href={buildHref(currentPage - 1)}
            className="border border-border px-3 py-1.5 text-sm transition-colors hover:border-foreground"
          >
            Previous
          </Link>
        ) : (
          <span className="border border-border px-3 py-1.5 text-sm text-muted">
            Previous
          </span>
        )}

        {pages.map((p, i) =>
          p === "..." ? (
            <span key={`ellipsis-${i}`} className="px-2 text-sm text-muted">
              ...
            </span>
          ) : p === currentPage ? (
            <span
              key={p}
              className="border border-foreground bg-foreground px-3 py-1.5 text-sm text-background"
            >
              {p}
            </span>
          ) : (
            <Link
              key={p}
              href={buildHref(p)}
              className="border border-border px-3 py-1.5 text-sm transition-colors hover:border-foreground"
            >
              {p}
            </Link>
          )
        )}

        {currentPage < totalPages ? (
          <Link
            href={buildHref(currentPage + 1)}
            className="border border-border px-3 py-1.5 text-sm transition-colors hover:border-foreground"
          >
            Next
          </Link>
        ) : (
          <span className="border border-border px-3 py-1.5 text-sm text-muted">
            Next
          </span>
        )}
      </div>
    </nav>
  );
}
