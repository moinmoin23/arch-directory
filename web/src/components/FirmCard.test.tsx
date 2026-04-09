import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FirmCard } from "./FirmCard";
import type { Firm } from "@/lib/queries/firms";

const baseFirm: Firm = {
  id: "test-id",
  slug: "test-firm",
  display_name: "Test Firm",
  canonical_name: "test firm",
  sector: "architecture",
  country: "US",
  city: "New York",
  website: "https://test.com",
  founded_year: 2000,
  size_range: "50-100",
  short_description: "A test architecture firm.",
  merged_into: null,
  publish_status: "published",
  quality_score: 80,
  country_code: "US",
  created_at: "2024-01-01",
  updated_at: "2024-01-01",
  last_seen_at: "2024-01-01",
  source_count: 0,
  wikidata_id: null,
  openalex_id: null,
  latitude: null,
  longitude: null,
  logo_url: null,
  image_url: null,
};

describe("FirmCard", () => {
  it("renders the firm name", () => {
    render(<FirmCard firm={baseFirm} />);
    expect(screen.getByText("Test Firm")).toBeInTheDocument();
  });

  it("renders location", () => {
    render(<FirmCard firm={baseFirm} />);
    expect(screen.getByText(/New York, US/)).toBeInTheDocument();
  });

  it("renders founded year", () => {
    render(<FirmCard firm={baseFirm} />);
    expect(screen.getByText(/Est\. 2000/)).toBeInTheDocument();
  });

  it("renders sector badge", () => {
    render(<FirmCard firm={baseFirm} />);
    expect(screen.getByText("architecture")).toBeInTheDocument();
  });

  it("renders description when present", () => {
    render(<FirmCard firm={baseFirm} />);
    expect(screen.getByText("A test architecture firm.")).toBeInTheDocument();
  });

  it("hides description when absent", () => {
    render(<FirmCard firm={{ ...baseFirm, short_description: null }} />);
    expect(screen.queryByText("A test architecture firm.")).not.toBeInTheDocument();
  });

  it("links to the correct URL", () => {
    render(<FirmCard firm={baseFirm} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/architecture/firms/test-firm");
  });

  it("maps multidisciplinary sector to technology path", () => {
    render(<FirmCard firm={{ ...baseFirm, sector: "multidisciplinary" }} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/technology/firms/test-firm");
  });
});
