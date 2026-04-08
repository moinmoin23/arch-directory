import Link from "next/link";

type Filter = {
  label: string;
  removeHref: string;
};

type Props = {
  filters: Filter[];
  clearAllHref: string;
};

export function FilterChips({ filters, clearAllHref }: Props) {
  if (filters.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {filters.map((f) => (
        <Link
          key={f.label}
          href={f.removeHref}
          className="inline-flex items-center gap-1.5 border border-border bg-foreground/5 px-2.5 py-1 text-xs transition-colors hover:border-foreground"
        >
          {f.label}
          <span aria-label={`Remove ${f.label} filter`}>×</span>
        </Link>
      ))}
      {filters.length > 1 && (
        <Link
          href={clearAllHref}
          className="px-2 py-1 text-xs text-muted underline hover:text-foreground"
        >
          Clear all
        </Link>
      )}
    </div>
  );
}
