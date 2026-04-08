import Link from "next/link";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

type Props = {
  activeLetter: string | null;
  basePath: string;
  /** Set of letters that have results — others render as disabled */
  availableLetters?: Set<string>;
  /** Extra search params to preserve */
  extraParams?: Record<string, string>;
};

export function AlphabetNav({
  activeLetter,
  basePath,
  availableLetters,
  extraParams = {},
}: Props) {
  function buildHref(letter: string | null) {
    const params = new URLSearchParams(extraParams);
    if (letter) params.set("letter", letter);
    const qs = params.toString();
    return qs ? `${basePath}?${qs}` : basePath;
  }

  return (
    <nav
      className="flex flex-wrap items-center gap-1"
      aria-label="Filter by first letter"
    >
      <Link
        href={buildHref(null)}
        className={`px-2 py-1 text-xs font-medium transition-colors ${
          !activeLetter
            ? "border border-foreground bg-foreground text-background"
            : "border border-border hover:border-foreground"
        }`}
      >
        All
      </Link>
      {LETTERS.map((letter) => {
        const available = !availableLetters || availableLetters.has(letter);
        const isActive = activeLetter === letter;

        if (!available) {
          return (
            <span
              key={letter}
              className="px-2 py-1 text-xs text-muted/40"
            >
              {letter}
            </span>
          );
        }

        return (
          <Link
            key={letter}
            href={buildHref(letter)}
            className={`px-2 py-1 text-xs font-medium transition-colors ${
              isActive
                ? "border border-foreground bg-foreground text-background"
                : "border border-border hover:border-foreground"
            }`}
          >
            {letter}
          </Link>
        );
      })}
    </nav>
  );
}
