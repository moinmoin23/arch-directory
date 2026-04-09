import type { Metadata } from "next";
import Link from "next/link";
import { getRolesWithCounts } from "@/lib/queries/people";

export const revalidate = 1800;

export const metadata: Metadata = {
  title: "People by Role",
  description:
    "Browse architects, researchers, designers, and other professionals by their role.",
};

function roleSlug(role: string) {
  return role.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "");
}

export default async function RolesIndexPage() {
  const roles = await getRolesWithCounts();

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">People by Role</h1>
      <p className="mt-2 text-muted">
        Browse professionals by their role in architecture, design, and
        technology.
      </p>

      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {roles.map(({ role, count }) => (
          <Link
            key={role}
            href={`/people/role/${roleSlug(role)}`}
            className="flex items-center justify-between border border-border p-4 transition-colors hover:border-foreground"
          >
            <span className="font-medium">{role}</span>
            <span className="text-sm text-muted">
              {count.toLocaleString()} {count !== 1 ? "people" : "person"}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
