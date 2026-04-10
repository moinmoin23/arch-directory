import { createServerClient } from "../supabase-server";
import type { Tables } from "../database.types";

export type Tag = Tables<"tags">;

export async function getTagBySlug(slug: string) {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("tags")
    .select("*")
    .eq("slug", slug)
    .single();

  if (error) return null;
  return data as Tag;
}

export async function getEntitiesForTag(tagId: string) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("entity_tags")
    .select("entity_id, entity_type")
    .eq("tag_id", tagId);

  const rows = data ?? [];
  const firmIds = rows.filter((r) => r.entity_type === "firm").map((r) => r.entity_id);
  const personIds = rows.filter((r) => r.entity_type === "person").map((r) => r.entity_id);

  const [firmsResult, peopleResult] = await Promise.all([
    firmIds.length > 0
      ? supabase
          .from("firms")
          .select("*")
          .in("id", firmIds)
          .eq("publish_status", "published")
          .is("merged_into", null)
          .order("display_name")
      : Promise.resolve({ data: [] }),
    personIds.length > 0
      ? supabase
          .from("people")
          .select("*, firms:current_firm_id(display_name, slug, sector)")
          .in("id", personIds)
          .eq("publish_status", "published")
          .order("display_name")
      : Promise.resolve({ data: [] }),
  ]);

  return {
    firms: (firmsResult.data ?? []) as Tables<"firms">[],
    people: (peopleResult.data ?? []) as unknown as Array<Tables<"people"> & { firms: Tables<"firms"> | null }>,
  };
}

export async function listTags() {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("tags")
    .select("*, entity_tags(count)")
    .order("name");

  if (error) {
    console.error("[tags.listTags]", error.message, error.details);
    return [];
  }

  return (data ?? []).map((tag) => ({
    ...tag,
    entity_count: (tag.entity_tags as unknown as Array<{ count: number }>)?.[0]?.count ?? 0,
  }));
}
