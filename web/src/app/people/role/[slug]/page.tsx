import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  listPeopleByRole,
  getRolesWithCounts,
} from "@/lib/queries/people";
import { PersonCard } from "@/components/PersonCard";
import { Pagination } from "@/components/Pagination";

export const revalidate = 1800;

const PER_PAGE = 36;

function roleSlug(role: string) {
  return role.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "");
}

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
};

export async function generateStaticParams() {
  const roles = await getRolesWithCounts();
  return roles.map((r) => ({ slug: roleSlug(r.role) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  // Convert slug back to display name
  const roles = await getRolesWithCounts();
  const match = roles.find((r) => roleSlug(r.role) === slug);
  const name = match?.role || slug;

  return {
    title: `${name}s in Architecture, Design & Technology`,
    description: `Browse ${name.toLowerCase()}s working in architecture, design, and technology. Part of TektonGraph.`,
  };
}

export default async function RolePeoplePage({
  params,
  searchParams,
}: Props) {
  const { slug } = await params;
  const sp = await searchParams;
  const page = Number(sp.page) || 1;

  // Map slug back to role name
  const roles = await getRolesWithCounts();
  const match = roles.find((r) => roleSlug(r.role) === slug);
  if (!match) notFound();

  const { people, count } = await listPeopleByRole(match.role, {
    page,
    perPage: PER_PAGE,
  });

  const totalPages = Math.ceil(count / PER_PAGE);

  function buildHref(pg: number) {
    if (pg <= 1) return `/people/role/${slug}`;
    return `/people/role/${slug}?page=${pg}`;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <nav className="text-sm text-muted">
        <Link href="/" className="hover:text-foreground">
          Home
        </Link>
        {" / "}
        <Link href="/people" className="hover:text-foreground">
          People
        </Link>
        {" / "}
        <Link href="/people/role" className="hover:text-foreground">
          By Role
        </Link>
        {" / "}
        <span>{match.role}</span>
      </nav>

      <h1 className="mt-4 text-3xl font-bold tracking-tight">
        {match.role}s
      </h1>
      <p className="mt-2 text-muted">
        {count.toLocaleString()} {match.role.toLowerCase()}
        {count !== 1 ? "s" : ""} in the directory.
      </p>

      <section className="mt-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {people.map((person) => (
            <PersonCard key={person.id} person={person} />
          ))}
        </div>
        {people.length === 0 && (
          <p className="py-12 text-center text-muted">No people found.</p>
        )}
      </section>

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        buildHref={buildHref}
        totalResults={count}
        perPage={PER_PAGE}
      />
    </div>
  );
}
