import { createServerClient } from "../supabase-server";
import type { Tables } from "../database.types";

export type Award = Tables<"awards">;
export type AwardWithRecipients = Award & {
  award_recipients: Array<{
    year: number | null;
    project_name: string | null;
    firms: Tables<"firms"> | null;
    people: Tables<"people"> | null;
  }>;
};

export async function listAwards(
  {
    page = 1,
    perPage = 36,
    organization,
  }: { page?: number; perPage?: number; organization?: string } = {}
) {
  const supabase = createServerClient();
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  let query = supabase
    .from("awards")
    .select("*", { count: "exact" })
    .order("year", { ascending: false })
    .order("award_name");

  if (organization) {
    query = query.eq("organization", organization);
  }

  const { data, error, count } = await query.range(from, to);

  if (error) return { awards: [], count: 0 };
  return { awards: data as Award[], count: count ?? 0 };
}

export async function getOrganizationsWithCounts(): Promise<
  { organization: string; count: number }[]
> {
  const supabase = createServerClient();
  const { data } = await supabase.from("awards").select("organization");

  if (!data) return [];

  const counts: Record<string, number> = {};
  for (const row of data) {
    if (row.organization) {
      counts[row.organization] = (counts[row.organization] || 0) + 1;
    }
  }

  return Object.entries(counts)
    .map(([organization, count]) => ({ organization, count }))
    .sort((a, b) => b.count - a.count);
}

export async function getAwardBySlug(slug: string) {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("awards")
    .select(`
      *,
      award_recipients(
        year,
        project_name,
        firms:firm_id(*),
        people:person_id(*)
      )
    `)
    .eq("slug", slug)
    .single();

  if (error) return null;
  return data as unknown as AwardWithRecipients;
}

export async function listAwardsByOrganization(organization: string) {
  const supabase = createServerClient();
  const { data } = await supabase
    .from("awards")
    .select("*")
    .eq("organization", organization)
    .order("year", { ascending: false });

  return data ?? [];
}
