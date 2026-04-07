import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { listFirmsBySector, listFirmsBySectorAndCountry } from "@/lib/queries/firms";
import { FirmCard } from "@/components/FirmCard";
import type { Enums } from "@/lib/database.types";

const VALID_SECTORS = ["architecture", "design", "technology"] as const;
type Sector = (typeof VALID_SECTORS)[number];

const SECTOR_LABELS: Record<Sector, string> = {
  architecture: "Architecture Firms",
  design: "Design Studios",
  technology: "Technology Labs",
};

type Props = {
  params: Promise<{ sector: string }>;
  searchParams: Promise<{ page?: string; country?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { sector } = await params;
  if (!VALID_SECTORS.includes(sector as Sector)) return {};

  const label = SECTOR_LABELS[sector as Sector];
  return {
    title: label,
    description: `Browse ${label.toLowerCase()} in the Arch Directory.`,
  };
}

export default async function SectorFirmsPage({ params, searchParams }: Props) {
  const { sector } = await params;
  const sp = await searchParams;

  if (!VALID_SECTORS.includes(sector as Sector)) notFound();

  const page = Number(sp.page) || 1;
  const country = sp.country;

  const { firms, count } = country
    ? await listFirmsBySectorAndCountry(
        sector as Enums<"sector_type">,
        country,
        { page }
      )
    : await listFirmsBySector(sector as Enums<"sector_type">, { page });

  const label = SECTOR_LABELS[sector as Sector];
  const totalPages = Math.ceil(count / 12);

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">
        {country ? `${label} in ${country}` : label}
      </h1>
      <p className="mt-2 text-muted">{count} results</p>

      <section className="mt-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {firms.map((firm) => (
            <FirmCard key={firm.id} firm={firm} />
          ))}
        </div>
        {firms.length === 0 && (
          <p className="text-muted">No firms found.</p>
        )}
      </section>

      {totalPages > 1 && (
        <nav className="mt-10 flex items-center gap-4 text-sm">
          {page > 1 && (
            <a
              href={`/${sector}/firms?page=${page - 1}${country ? `&country=${country}` : ""}`}
              className="border border-border px-4 py-2 hover:border-foreground"
            >
              Previous
            </a>
          )}
          <span className="text-muted">
            Page {page} of {totalPages}
          </span>
          {page < totalPages && (
            <a
              href={`/${sector}/firms?page=${page + 1}${country ? `&country=${country}` : ""}`}
              className="border border-border px-4 py-2 hover:border-foreground"
            >
              Next
            </a>
          )}
        </nav>
      )}
    </div>
  );
}
