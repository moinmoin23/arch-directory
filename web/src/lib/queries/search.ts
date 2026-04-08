import { createServerClient } from "../supabase-server";

export type SearchResult = {
  entity_type: "firm" | "person";
  id: string;
  slug: string;
  display_name: string;
  sector: string;
  country: string | null;
  city: string | null;
  short_description: string | null;
  role: string | null;
  rank: number;
};

export async function searchDirectory(
  query: string,
  {
    limit = 12,
    sector,
    country,
  }: { limit?: number; sector?: string; country?: string } = {}
): Promise<{ firms: SearchResult[]; people: SearchResult[] }> {
  if (!query.trim()) {
    return { firms: [], people: [] };
  }

  const supabase = createServerClient();
  const { data, error } = await supabase.rpc("search_directory", {
    query: query.trim(),
    result_limit: limit,
    sector_filter: sector || null,
    country_filter: country || null,
  });

  if (error || !data) {
    return { firms: [], people: [] };
  }

  const results = data as SearchResult[];
  return {
    firms: results.filter((r) => r.entity_type === "firm"),
    people: results.filter((r) => r.entity_type === "person"),
  };
}
