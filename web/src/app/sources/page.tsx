import type { Metadata } from "next";
import { listSources } from "@/lib/queries/sources";
import { SourceList } from "@/components/SourceList";

export const metadata: Metadata = {
  title: "Sources & Publications",
  description:
    "Articles, publications, and press coverage tracked by the Arch Directory.",
};

export default async function SourcesPage() {
  const { sources, count } = await listSources();

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">
        Sources &amp; Publications
      </h1>
      <p className="mt-2 text-muted">{count} sources tracked.</p>

      <SourceList sources={sources} />

      {sources.length === 0 && (
        <p className="mt-8 text-muted">No sources yet.</p>
      )}
    </div>
  );
}
