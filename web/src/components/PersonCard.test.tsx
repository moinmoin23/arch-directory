import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PersonCard } from "./PersonCard";
import type { PersonWithFirm } from "@/lib/queries/people";

const basePerson: PersonWithFirm = {
  id: "person-id",
  slug: "jane-doe",
  display_name: "Jane Doe",
  canonical_name: "jane doe",
  role: "Principal",
  title: null,
  sector: "architecture",
  current_firm_id: "firm-id",
  nationality: "US",
  bio: "An accomplished architect.",
  publish_status: "published",
  quality_score: 70,
  created_at: "2024-01-01",
  updated_at: "2024-01-01",
  last_seen_at: "2024-01-01",
  source_count: 0,
  wikidata_id: null,
  openalex_id: null,
  orcid: null,
  birth_year: null,
  death_year: null,
  image_url: null,
  firms: {
    id: "firm-id",
    slug: "test-firm",
    display_name: "Test Firm",
    canonical_name: "test firm",
    sector: "architecture",
    country: "US",
    city: "New York",
    website: "https://test.com",
    founded_year: 2000,
    size_range: null,
    short_description: null,
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
  },
};

describe("PersonCard", () => {
  it("renders the person name", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("renders role and firm", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText(/Principal at Test Firm/)).toBeInTheDocument();
  });

  it("renders bio when present", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("An accomplished architect.")).toBeInTheDocument();
  });

  it("hides bio when absent", () => {
    render(<PersonCard person={{ ...basePerson, bio: null }} />);
    expect(screen.queryByText("An accomplished architect.")).not.toBeInTheDocument();
  });

  it("renders sector badge", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("architecture")).toBeInTheDocument();
  });

  it("links to the correct URL", () => {
    render(<PersonCard person={basePerson} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/people/jane-doe");
  });

  it("renders without firm association", () => {
    render(<PersonCard person={{ ...basePerson, firms: null }} />);
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.queryByText(/at Test Firm/)).not.toBeInTheDocument();
  });
});
