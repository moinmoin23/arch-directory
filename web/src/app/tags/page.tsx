import type { Metadata } from "next";
import Link from "next/link";
import { listTags } from "@/lib/queries/tags";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Tags",
  description: "Browse firms and people by topic on TektonGraph.",
};

export default async function TagsPage() {
  const tags = await listTags();

  // Group by category
  const grouped = new Map<string, typeof tags>();
  for (const tag of tags) {
    if (tag.entity_count === 0) continue;
    const cat = tag.category || "Other";
    const list = grouped.get(cat) ?? [];
    list.push(tag);
    grouped.set(cat, list);
  }

  const categories = [...grouped.keys()].sort();

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Tags</h1>
      <p className="mt-2 text-muted">
        Browse firms and people by topic.
      </p>

      {categories.map((category) => (
        <section key={category} className="mt-10">
          <h2 className="text-lg font-semibold mb-3 capitalize">{category}</h2>
          <div className="flex flex-wrap gap-2">
            {grouped.get(category)!.map((tag) => (
              <Link
                key={tag.slug}
                href={`/tags/${tag.slug}`}
                className="border border-border px-3 py-1.5 text-sm text-muted hover:border-foreground hover:text-foreground transition-colors"
              >
                {tag.name}
                <span className="ml-1.5 text-xs opacity-60">
                  {tag.entity_count}
                </span>
              </Link>
            ))}
          </div>
        </section>
      ))}

      {categories.length === 0 && (
        <p className="mt-12 text-center text-muted">No tags yet.</p>
      )}
    </div>
  );
}
