import { createServerClient } from "../supabase-server";
import type { Tables, Enums } from "../database.types";

type SectorType = Enums<"sector_type">;

export type Firm = Tables<"firms">;
export type FirmWithPeople = Firm & {
  firm_people: Array<{
    role: string | null;
    is_current: boolean;
    people: Tables<"people">;
  }>;
};

const FIRM_SELECT = `*, firm_people(role, is_current, people:people(*))` as const;

export async function getFirmBySlug(slug: string) {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("firms")
    .select(FIRM_SELECT)
    .eq("slug", slug)
    .single();

  if (error) return null;
  return data as unknown as FirmWithPeople;
}

export async function listFirmsBySector(
  sector: SectorType,
  { page = 1, perPage = 12 }: { page?: number; perPage?: number } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("firms")
    .select("*", { count: "exact" })
    .eq("sector", sector)
    .eq("publish_status", "published")
    .is("merged_into", null)
    .order("display_name")
    .range(from, to);

  if (error) return { firms: [], count: 0 };
  return { firms: data as Firm[], count: count ?? 0 };
}

export async function listFirmsByCountry(
  country: string,
  { page = 1, perPage = 12 }: { page?: number; perPage?: number } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("firms")
    .select("*", { count: "exact" })
    .eq("country", country)
    .eq("publish_status", "published")
    .is("merged_into", null)
    .order("display_name")
    .range(from, to);

  if (error) return { firms: [], count: 0 };
  return { firms: data as Firm[], count: count ?? 0 };
}

export async function listFirmsBySectorAndCountry(
  sector: SectorType,
  country: string,
  { page = 1, perPage = 12 }: { page?: number; perPage?: number } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("firms")
    .select("*", { count: "exact" })
    .eq("sector", sector)
    .eq("country", country)
    .eq("publish_status", "published")
    .is("merged_into", null)
    .order("display_name")
    .range(from, to);

  if (error) return { firms: [], count: 0 };
  return { firms: data as Firm[], count: count ?? 0 };
}

export async function getFirmAliases(firmId: string) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("entity_aliases")
    .select("alias")
    .eq("entity_id", firmId)
    .eq("entity_type", "firm");

  return data?.map((a) => a.alias) ?? [];
}

export async function getFirmAwards(firmId: string) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("award_recipients")
    .select("year, project_name, awards(*)")
    .eq("firm_id", firmId);

  return data ?? [];
}

export async function getFirmSources(firmId: string) {
  const supabase = createServerClient();
  // entity_sources table added in migration 20260409000001
  // After running migrations + `npm run db:types`, remove the type assertion
  const { data, error } = await (supabase as any)
    .from("entity_sources")
    .select("mention_type, sources(*)")
    .eq("entity_id", firmId)
    .eq("entity_type", "firm")
    .order("created_at", { ascending: false })
    .limit(20);

  if (error) {
    console.error("[firms.getFirmSources]", error.message, error.details);
    return [];
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data ?? [])
    .map((row: any) => row.sources)
    .filter((s: any): s is Tables<"sources"> => s !== null);
}

export async function listFirmsByCountry2(
  country: string,
  {
    page = 1,
    perPage = 36,
    sector,
  }: { page?: number; perPage?: number; sector?: SectorType } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  let query = supabase
    .from("firms")
    .select("*", { count: "exact" })
    .eq("country", country)
    .eq("publish_status", "published")
    .is("merged_into", null)
    .order("display_name")
    .range(from, to);

  if (sector) {
    query = query.eq("sector", sector);
  }

  const { data, error, count } = await query;

  if (error) return { firms: [], count: 0 };
  return { firms: data as Firm[], count: count ?? 0 };
}

export async function getCountriesWithCounts(): Promise<
  { country: string; count: number }[]
> {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("firms")
    .select("country")
    .eq("publish_status", "published")
    .is("merged_into", null);

  if (!data) return [];

  const counts: Record<string, number> = {};
  for (const row of data) {
    if (row.country) {
      counts[row.country] = (counts[row.country] || 0) + 1;
    }
  }

  return Object.entries(counts)
    .map(([country, count]) => ({ country, count }))
    .sort((a, b) => b.count - a.count);
}

export async function countFirmsBySector() {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("firms")
    .select("sector", { count: "exact", head: false })
    .eq("publish_status", "published")
    .is("merged_into", null);

  const counts: Record<string, number> = {
    architecture: 0,
    design: 0,
    technology: 0,
    multidisciplinary: 0,
  };

  if (data) {
    for (const row of data) {
      counts[row.sector] = (counts[row.sector] || 0) + 1;
    }
  }

  return counts;
}
