"use client";

export default function GlobalError({
  error: _error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  void _error;

  return (
    <html lang="en">
      <body className="min-h-screen flex items-center justify-center">
        <div className="text-center px-6">
          <h1 className="text-4xl font-bold tracking-tight">
            Something went wrong
          </h1>
          <p className="mt-4 text-lg text-gray-500">
            An unexpected error occurred. Please try again.
          </p>
          <button
            onClick={() => unstable_retry()}
            className="mt-8 border border-gray-900 bg-gray-900 px-5 py-2.5 text-sm text-white transition-colors hover:bg-transparent hover:text-gray-900"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
