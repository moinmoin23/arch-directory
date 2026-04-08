import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  listFirmsByCountry2,
  getCountriesWithCounts,
} from "@/lib/queries/firms";
import { FirmCard } from "@/components/FirmCard";
import { Pagination } from "@/components/Pagination";

const PER_PAGE = 36;

// Common country code to name mapping for SEO titles
const COUNTRY_NAMES: Record<string, string> = {
  US: "United States", GB: "United Kingdom", DE: "Germany", FR: "France",
  IT: "Italy", ES: "Spain", NL: "Netherlands", CH: "Switzerland",
  AT: "Austria", BE: "Belgium", SE: "Sweden", NO: "Norway", DK: "Denmark",
  FI: "Finland", PT: "Portugal", IE: "Ireland", PL: "Poland", CZ: "Czechia",
  GR: "Greece", RU: "Russia", TR: "Turkey", AU: "Australia", NZ: "New Zealand",
  CA: "Canada", MX: "Mexico", BR: "Brazil", AR: "Argentina", CL: "Chile",
  CO: "Colombia", PE: "Peru", CN: "China", JP: "Japan", KR: "South Korea",
  IN: "India", SG: "Singapore", HK: "Hong Kong", TW: "Taiwan", TH: "Thailand",
  MY: "Malaysia", ID: "Indonesia", PH: "Philippines", VN: "Vietnam",
  AE: "UAE", SA: "Saudi Arabia", IL: "Israel", EG: "Egypt", ZA: "South Africa",
  NG: "Nigeria", KE: "Kenya", MA: "Morocco",
};

function countryName(code: string) {
  return COUNTRY_NAMES[code.toUpperCase()] || code.toUpperCase();
}

type Props = {
  params: Promise<{ code: string }>;
  searchParams: Promise<{ page?: string }>;
};

export async function generateStaticParams() {
  const countries = await getCountriesWithCounts();
  // Only generate pages for countries with 3+ firms
  return countries
    .filter((c) => c.count >= 3)
    .map((c) => ({ code: c.country.toLowerCase() }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { code } = await params;
  const name = countryName(code);
  return {
    title: `Architecture, Design & Technology Firms in ${name}`,
    description: `Browse firms, studios, and labs in ${name}. Part of the Arch Directory — the global directory of architecture, design, and technology.`,
  };
}

export default async function CountryFirmsPage({
  params,
  searchParams,
}: Props) {
  const { code } = await params;
  const sp = await searchParams;
  const page = Number(sp.page) || 1;

  const upperCode = code.toUpperCase();
  const { firms, count } = await listFirmsByCountry2(upperCode, {
    page,
    perPage: PER_PAGE,
  });

  if (count === 0 && page === 1) notFound();

  const totalPages = Math.ceil(count / PER_PAGE);
  const name = countryName(code);

  function buildHref(pg: number) {
    if (pg <= 1) return `/firms/country/${code.toLowerCase()}`;
    return `/firms/country/${code.toLowerCase()}?page=${pg}`;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <nav className="text-sm text-muted">
        <Link href="/" className="hover:text-foreground">
          Home
        </Link>
        {" / "}
        <Link href="/firms/country" className="hover:text-foreground">
          Firms by Country
        </Link>
        {" / "}
        <span>{name}</span>
      </nav>

      <h1 className="mt-4 text-3xl font-bold tracking-tight">
        Firms in {name}
      </h1>
      <p className="mt-2 text-muted">
        {count.toLocaleString()} firm{count !== 1 ? "s" : ""} in the directory.
      </p>

      <section className="mt-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {firms.map((firm) => (
            <FirmCard key={firm.id} firm={firm} />
          ))}
        </div>
      </section>

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        buildHref={buildHref}
        totalResults={count}
        perPage={PER_PAGE}
      />
    </div>
  );
}
