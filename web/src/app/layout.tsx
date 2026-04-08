import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Arch Directory — Architecture, Design & Technology",
    template: "%s | Arch Directory",
  },
  description:
    "The global directory of architecture firms, design studios, technology labs, and the people behind them.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"
  ),
  openGraph: {
    type: "website",
    siteName: "Arch Directory",
  },
};

const NAV_LINKS = [
  { href: "/architecture", label: "Architecture" },
  { href: "/design", label: "Design" },
  { href: "/technology", label: "Technology" },
  { href: "/people", label: "People" },
  { href: "/awards", label: "Awards" },
  { href: "/search", label: "Search" },
] as const;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-border">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link
              href="/"
              className="text-lg font-semibold tracking-tight"
            >
              Arch Directory
            </Link>
            <ul className="flex items-center gap-6 text-sm">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-muted transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-border">
          <div className="mx-auto max-w-6xl px-6 py-8 text-sm text-muted">
            <p>Arch Directory — Architecture, Design & Technology</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
