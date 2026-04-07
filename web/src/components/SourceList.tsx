import type { Source } from "@/lib/queries/sources";

export function SourceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold mb-4">Sources &amp; Publications</h2>
      <ul className="space-y-3">
        {sources.map((source) => (
          <li key={source.id} className="border border-border p-4">
            <div className="flex items-baseline justify-between gap-4">
              <div>
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium hover:underline"
                  >
                    {source.title}
                  </a>
                ) : (
                  <span className="font-medium">{source.title}</span>
                )}
                <p className="mt-1 text-sm text-muted">
                  {source.source_name}
                  {source.author ? ` — ${source.author}` : ""}
                </p>
              </div>
              {source.published_at && (
                <time className="shrink-0 text-xs text-muted">
                  {new Date(source.published_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </time>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
