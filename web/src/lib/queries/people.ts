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
  { page = 1, perPage = 12 }: { page?: number; perPage?: number } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("people")
    .select("*, firms:current_firm_id(display_name, slug, sector)", { count: "exact" })
    .eq("publish_status", "published")
    .order("display_name")
    .range(from, to);

  if (error) return { people: [], count: 0 };
  return { people: data as unknown as PersonWithFirm[], count: count ?? 0 };
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
