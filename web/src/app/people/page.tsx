import type { Metadata } from "next";
import { listPeople } from "@/lib/queries/people";
import { PersonCard } from "@/components/PersonCard";

export const metadata: Metadata = {
  title: "People",
  description:
    "Architects, designers, researchers, and technologists shaping the built environment.",
};

export default async function PeoplePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;

  const { people, count } = await listPeople({ page });

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">People</h1>
      <p className="mt-2 text-muted">
        {count} people in the directory.
      </p>

      <section className="mt-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {people.map((person) => (
            <PersonCard key={person.id} person={person} />
          ))}
        </div>
        {people.length === 0 && (
          <p className="text-muted">No people found.</p>
        )}
      </section>
    </div>
  );
}
