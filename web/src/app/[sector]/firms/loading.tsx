function SkeletonCard() {
  return (
    <div className="border border-border p-5 animate-pulse">
      <div className="h-5 w-2/3 rounded bg-border" />
      <div className="mt-2 h-4 w-1/2 rounded bg-border" />
      <div className="mt-3 h-4 w-full rounded bg-border" />
      <div className="mt-1 h-4 w-4/5 rounded bg-border" />
      <div className="mt-3 flex gap-2">
        <div className="h-5 w-16 rounded bg-border" />
        <div className="h-5 w-20 rounded bg-border" />
      </div>
    </div>
  );
}

export default function FirmsLoading() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <div className="h-8 w-48 rounded bg-border animate-pulse" />
      <div className="mt-2 h-5 w-32 rounded bg-border animate-pulse" />

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 12 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}
