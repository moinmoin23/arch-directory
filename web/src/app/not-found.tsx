import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20 text-center">
      <h1 className="text-4xl font-bold tracking-tight">404</h1>
      <p className="mt-4 text-lg text-muted">
        The page you are looking for does not exist.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link
          href="/"
          className="border border-foreground bg-foreground px-5 py-2.5 text-sm text-background transition-colors hover:bg-transparent hover:text-foreground"
        >
          Go home
        </Link>
        <Link
          href="/search"
          className="border border-border px-5 py-2.5 text-sm transition-colors hover:border-foreground"
        >
          Search the directory
        </Link>
      </div>
    </div>
  );
}
