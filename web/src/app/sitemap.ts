import type { MetadataRoute } from "next";
import { createServerClient } from "@/lib/supabase-server";
import { getCountriesWithCounts } from "@/lib/queries/firms";
import { getRolesWithCounts } from "@/lib/queries/people";

const BASE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://tektongraph.com";

function roleSlug(role: string) {
  return role.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "");
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const supabase = createServerClient();
  const entries: MetadataRoute.Sitemap = [];

  // Static pages
  entries.push(
    { url: BASE_URL, changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE_URL}/search`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE_URL}/architecture`, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE_URL}/design`, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE_URL}/technology`, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE_URL}/people`, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE_URL}/awards`, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/firms/country`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE_URL}/people/role`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE_URL}/architecture/firms`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE_URL}/design/firms`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE_URL}/technology/firms`, changeFrequency: "weekly", priority: 0.8 }
  );

  // Published firms
  const { data: firms } = await supabase
    .from("firms")
    .select("slug, sector, updated_at")
    .eq("publish_status", "published")
    .is("merged_into", null);

  if (firms) {
    for (const firm of firms) {
      const sector =
        firm.sector === "multidisciplinary" ? "technology" : firm.sector;
      entries.push({
        url: `${BASE_URL}/${sector}/firms/${firm.slug}`,
        lastModified: firm.updated_at,
        changeFrequency: "monthly",
        priority: 0.7,
      });
    }
  }

  // Published people
  const { data: people } = await supabase
    .from("people")
    .select("slug, updated_at")
    .eq("publish_status", "published");

  if (people) {
    for (const person of people) {
      entries.push({
        url: `${BASE_URL}/people/${person.slug}`,
        lastModified: person.updated_at,
        changeFrequency: "monthly",
        priority: 0.6,
      });
    }
  }

  // Country pages (3+ firms)
  const countries = await getCountriesWithCounts();
  for (const { country, count } of countries) {
    if (count >= 3) {
      entries.push({
        url: `${BASE_URL}/firms/country/${country.toLowerCase()}`,
        changeFrequency: "weekly",
        priority: 0.7,
      });
    }
  }

  // Role pages
  const roles = await getRolesWithCounts();
  for (const { role } of roles) {
    entries.push({
      url: `${BASE_URL}/people/role/${roleSlug(role)}`,
      changeFrequency: "weekly",
      priority: 0.7,
    });
  }

  // Award pages
  const { data: awards } = await supabase
    .from("awards")
    .select("slug");

  if (awards) {
    for (const award of awards) {
      entries.push({
        url: `${BASE_URL}/awards/${award.slug}`,
        changeFrequency: "yearly",
        priority: 0.6,
      });
    }
  }

  return entries;
}
