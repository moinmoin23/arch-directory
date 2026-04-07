import type { Metadata } from "next";
import { listFirmsBySector } from "@/lib/queries/firms";
import { listPeopleBySector } from "@/lib/queries/people";
import { FirmCard } from "@/components/FirmCard";
import { PersonCard } from "@/components/PersonCard";

export const metadata: Metadata = {
  title: "Architecture Firms & Practices",
  description:
    "Browse architecture firms and practices worldwide — from emerging studios to Pritzker-winning offices.",
};

export default async function ArchitecturePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; country?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;

  const [{ firms, count }, { people }] = await Promise.all([
    listFirmsBySector("architecture", { page }),
    listPeopleBySector("architecture", { perPage: 6 }),
  ]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Architecture</h1>
      <p className="mt-2 text-muted">
        {count} firms and practices in the directory.
      </p>

      <section className="mt-10">
        <h2 className="text-xl font-semibold mb-6">Firms</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {firms.map((firm) => (
            <FirmCard key={firm.id} firm={firm} />
          ))}
        </div>
        {firms.length === 0 && (
          <p className="text-muted">No firms found.</p>
        )}
      </section>

      {people.length > 0 && (
        <section className="mt-16">
          <h2 className="text-xl font-semibold mb-6">Notable People</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {people.map((person) => (
              <PersonCard key={person.id} person={person} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
