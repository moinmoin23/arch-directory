/**
 * Inline search bar that navigates to /search with optional pre-set filters.
 * Use on every listing page so users can search within context.
 */
type Props = {
  placeholder?: string;
  /** Pre-fill the sector filter on /search */
  sector?: string;
  className?: string;
};

export function SearchBar({
  placeholder = "Search the directory...",
  sector,
  className = "",
}: Props) {
  return (
    <form action="/search" method="GET" className={`flex gap-2 ${className}`}>
      {sector && <input type="hidden" name="sector" value={sector} />}
      <input
        type="text"
        name="q"
        placeholder={placeholder}
        className="flex-1 border border-border bg-transparent px-4 py-2 text-sm placeholder:text-muted/60 focus:border-foreground focus:outline-none"
      />
      <button
        type="submit"
        className="border border-foreground bg-foreground px-4 py-2 text-sm text-background transition-colors hover:bg-transparent hover:text-foreground"
      >
        Search
      </button>
    </form>
  );
}
