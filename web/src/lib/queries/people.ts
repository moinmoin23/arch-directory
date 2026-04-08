import { createServerClient } from "../supabase-server";
import type { Tables, Enums } from "../database.types";

type SectorType = Enums<"sector_type">;

export type Person = Tables<"people">;
export type PersonWithFirm = Person & {
  firms: Tables<"firms"> | null;
};

export async function getPersonBySlug(slug: string) {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("people")
    .select("*, firms:current_firm_id(*)")
    .eq("slug", slug)
    .single();

  if (error) return null;
  return data as unknown as PersonWithFirm;
}

export async function listPeople(
  {
    page = 1,
    perPage = 36,
    letter,
    sector,
    sort = "name",
  }: {
    page?: number;
    perPage?: number;
    letter?: string;
    sector?: SectorType;
    sort?: "name" | "recent";
  } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  let query = supabase
    .from("people")
    .select("*, firms:current_firm_id(display_name, slug, sector)", { count: "exact" })
    .eq("publish_status", "published");

  if (letter && /^[A-Z]$/.test(letter)) {
    query = query.gte("display_name", letter).lt("display_name", String.fromCharCode(letter.charCodeAt(0) + 1));
  }

  if (sector) {
    query = query.eq("sector", sector);
  }

  if (sort === "recent") {
    query = query.order("created_at", { ascending: false });
  } else {
    query = query.order("display_name");
  }

  const { data, error, count } = await query.range(from, to);

  if (error) return { people: [], count: 0 };
  return { people: data as unknown as PersonWithFirm[], count: count ?? 0 };
}

export async function getPeopleLetterCounts() {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("people")
    .select("display_name")
    .eq("publish_status", "published");

  const letters = new Set<string>();
  if (data) {
    for (const p of data) {
      const first = p.display_name?.charAt(0)?.toUpperCase();
      if (first && /[A-Z]/.test(first)) letters.add(first);
    }
  }
  return letters;
}

export async function listPeopleByRole(
  role: string,
  { page = 1, perPage = 12 }: { page?: number; perPage?: number } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("people")
    .select("*, firms:current_firm_id(display_name, slug, sector)", { count: "exact" })
    .eq("publish_status", "published")
    .ilike("role", `%${role}%`)
    .order("display_name")
    .range(from, to);

  if (error) return { people: [], count: 0 };
  return { people: data as unknown as PersonWithFirm[], count: count ?? 0 };
}

export async function listPeopleBySector(
  sector: SectorType,
  { page = 1, perPage = 12 }: { page?: number; perPage?: number } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("people")
    .select("*, firms:current_firm_id(display_name, slug, sector)", { count: "exact" })
    .eq("publish_status", "published")
    .eq("sector", sector)
    .order("display_name")
    .range(from, to);

  if (error) return { people: [], count: 0 };
  return { people: data as unknown as PersonWithFirm[], count: count ?? 0 };
}

export async function getPersonAwards(personId: string) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("award_recipients")
    .select("year, project_name, awards(*)")
    .eq("person_id", personId);

  return data ?? [];
}

export async function getPersonAliases(personId: string) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("entity_aliases")
    .select("alias")
    .eq("entity_id", personId)
    .eq("entity_type", "person");

  return data?.map((a) => a.alias) ?? [];
}
