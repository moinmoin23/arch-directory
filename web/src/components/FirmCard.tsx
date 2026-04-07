import Link from "next/link";
import type { Firm } from "@/lib/queries/firms";

export function FirmCard({ firm }: { firm: Firm }) {
  const sectorPath = firm.sector === "multidisciplinary" ? "technology" : firm.sector;

  return (
    <Link
      href={`/${sectorPath}/firms/${firm.slug}`}
      className="group block border border-border p-5 transition-colors hover:border-foreground"
    >
      <h3 className="font-semibold group-hover:underline">
        {firm.display_name}
      </h3>
      <p className="mt-1 text-sm text-muted">
        {[firm.city, firm.country].filter(Boolean).join(", ")}
        {firm.founded_year ? ` · Est. ${firm.founded_year}` : ""}
      </p>
      {firm.short_description && (
        <p className="mt-2 text-sm text-muted line-clamp-2">
          {firm.short_description}
        </p>
      )}
      <div className="mt-3 flex items-center gap-2">
        <span className="inline-block border border-border px-2 py-0.5 text-xs text-muted">
          {firm.sector}
        </span>
        {firm.size_range && (
          <span className="text-xs text-muted">{firm.size_range} people</span>
        )}
      </div>
    </Link>
  );
}
