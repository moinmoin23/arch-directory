import Link from "next/link";
import type { PersonWithFirm } from "@/lib/queries/people";

export function PersonCard({ person }: { person: PersonWithFirm }) {
  return (
    <Link
      href={`/people/${person.slug}`}
      className="group flex gap-4 border border-border p-5 transition-colors hover:border-foreground"
    >
      {person.image_url && (
        <img
          src={person.image_url}
          alt={person.display_name}
          className="h-16 w-16 rounded-full object-cover flex-shrink-0"
        />
      )}
      <div className="min-w-0">
      <h3 className="font-semibold group-hover:underline">
        {person.display_name}
      </h3>
      <p className="mt-1 text-sm text-muted">
        {person.role}
        {person.firms ? ` at ${person.firms.display_name}` : ""}
      </p>
      {person.bio && (
        <p className="mt-2 text-sm text-muted line-clamp-2">{person.bio}</p>
      )}
      <div className="mt-3">
        <span className="inline-block border border-border px-2 py-0.5 text-xs text-muted">
          {person.sector}
        </span>
      </div>
    </div>
    </Link>
  );
}
