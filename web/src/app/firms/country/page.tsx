import type { Metadata } from "next";
import Link from "next/link";
import { getCountriesWithCounts } from "@/lib/queries/firms";

export const metadata: Metadata = {
  title: "Firms by Country",
  description:
    "Browse architecture firms, design studios, and technology labs by country.",
};

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
  return COUNTRY_NAMES[code] || code;
}

export default async function CountriesIndexPage() {
  const countries = await getCountriesWithCounts();

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Firms by Country</h1>
      <p className="mt-2 text-muted">
        Browse {countries.length} countries with firms in the directory.
      </p>

      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {countries.map(({ country, count }) => (
          <Link
            key={country}
            href={`/firms/country/${country.toLowerCase()}`}
            className="flex items-center justify-between border border-border p-4 transition-colors hover:border-foreground"
          >
            <span className="font-medium">{countryName(country)}</span>
            <span className="text-sm text-muted">
              {count} firm{count !== 1 ? "s" : ""}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
