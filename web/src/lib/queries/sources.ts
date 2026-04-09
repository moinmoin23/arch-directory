import { createServerClient } from "../supabase-server";
import type { Tables, Enums } from "../database.types";

type SectorType = Enums<"sector_type">;

export type Source = Tables<"sources">;

export async function listSources(
  { page = 1, perPage = 20 }: { page?: number; perPage?: number } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("sources")
    .select("*", { count: "exact" })
    .order("published_at", { ascending: false })
    .range(from, to);

  if (error) {
    console.error("[sources.listSources]", error.message, error.details);
    return { sources: [], count: 0 };
  }
  return { sources: data as Source[], count: count ?? 0 };
}

export async function listSourcesByName(sourceName: string) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("sources")
    .select("*")
    .eq("source_name", sourceName)
    .order("published_at", { ascending: false });

  return data ?? [];
}

export async function listSourcesBySector(sector: SectorType) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("sources")
    .select("*")
    .eq("sector", sector)
    .order("published_at", { ascending: false })
    .limit(20);

  return data ?? [];
}
