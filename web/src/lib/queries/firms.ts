import { cache } from "react";
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

export const getFirmBySlug = cache(async (slug: string) => {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("firms")
    .select(FIRM_SELECT)
    .eq("slug", slug)
    .single();

  if (error) return null;
  return data as unknown as FirmWithPeople;
});

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

  if (error) {
    console.error("[firms.listFirmsBySector]", error.message, error.details);
    return { firms: [], count: 0 };
  }
  return { firms: data as Firm[], count: count ?? 0 };
}

export async function listFirmsByCountry(
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

  if (error) {
    console.error("[firms.listFirmsByCountry]", error.message, error.details);
    return { firms: [], count: 0 };
  }
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

  if (error) {
    console.error("[firms.listFirmsBySectorAndCountry]", error.message, error.details);
    return { firms: [], count: 0 };
  }
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
  const { data, error } = await supabase
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

  return (data ?? [])
    .map((row) => row.sources)
    .filter((s): s is Tables<"sources"> => s !== null);
}

export async function getFirmSourceCounts(firmIds: string[]): Promise<Map<string, number>> {
  if (firmIds.length === 0) return new Map();
  const supabase = createServerClient();
  const { data, error } = await supabase.rpc("get_entity_source_counts", {
    p_entity_ids: firmIds,
    p_entity_type: "firm",
  });

  const map = new Map<string, number>();
  if (error) {
    console.error("[firms.getFirmSourceCounts]", error.message, error.details);
    return map;
  }
  for (const row of data ?? []) {
    map.set(row.entity_id, Number(row.source_count));
  }
  return map;
}

export async function getCountriesWithCounts(): Promise<
  { country: string; count: number }[]
> {
  const supabase = createServerClient();
  const { data, error } = await supabase.rpc("count_firms_by_country");

  if (error) {
    console.error("[firms.getCountriesWithCounts]", error.message, error.details);
    return [];
  }
  return data ?? [];
}

export async function countFirmsBySector() {
  const supabase = createServerClient();
  const { data, error } = await supabase.rpc("count_firms_by_sector");

  const counts: Record<string, number> = {
    architecture: 0,
    design: 0,
    technology: 0,
    multidisciplinary: 0,
  };

  if (error) {
    console.error("[firms.countFirmsBySector]", error.message, error.details);
    return counts;
  }

  if (data) {
    for (const row of data) {
      counts[row.sector] = row.count;
    }
  }

  return counts;
}
