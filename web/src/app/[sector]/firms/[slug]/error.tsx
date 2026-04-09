"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function FirmErrorPage({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-4xl px-6 py-20 text-center">
      <h1 className="text-3xl font-bold tracking-tight">
        Could not load firm
      </h1>
      <p className="mt-4 text-muted">
        There was a problem loading this firm&apos;s page.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <button
          onClick={() => unstable_retry()}
          className="border border-foreground bg-foreground px-5 py-2.5 text-sm text-background transition-colors hover:bg-transparent hover:text-foreground"
        >
          Try again
        </button>
        <Link
          href="/"
          className="border border-border px-5 py-2.5 text-sm transition-colors hover:border-foreground"
        >
          Go home
        </Link>
      </div>
    </div>
  );
}
