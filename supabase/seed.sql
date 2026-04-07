-- ============================================================
-- Seed data: 25 entities across architecture, design, and technology
-- ============================================================

-- ============================================================
-- FIRMS (10)
-- ============================================================

-- Architecture firms
insert into firms (id, slug, display_name, canonical_name, sector, country, city, website, founded_year, size_range, short_description)
values
  ('a0000000-0000-0000-0000-000000000001', 'big-bjarke-ingels-group', 'BIG – Bjarke Ingels Group', 'big bjarke ingels group', 'architecture', 'Denmark', 'Copenhagen', 'https://big.dk', 2005, '500+', 'Danish architecture firm known for pragmatic utopian design, blending sustainability with bold geometric forms.'),
  ('a0000000-0000-0000-0000-000000000002', 'mvrdv', 'MVRDV', 'mvrdv', 'architecture', 'Netherlands', 'Rotterdam', 'https://www.mvrdv.nl', 1993, '200-500', 'Dutch firm exploring density, public space, and landscape through inventive and data-driven architecture.'),
  ('a0000000-0000-0000-0000-000000000003', 'zaha-hadid-architects', 'Zaha Hadid Architects', 'zaha hadid architects', 'architecture', 'United Kingdom', 'London', 'https://www.zaha-hadid.com', 1980, '500+', 'Global practice known for parametric design, fluid forms, and pioneering computational architecture.'),
  ('a0000000-0000-0000-0000-000000000004', 'snohetta', 'Snøhetta', 'snohetta', 'architecture', 'Norway', 'Oslo', 'https://snohetta.com', 1989, '200-500', 'Transdisciplinary practice integrating architecture, landscape, interiors, and graphic design.')
on conflict (slug) do update set
  display_name = excluded.display_name,
  canonical_name = excluded.canonical_name,
  sector = excluded.sector,
  country = excluded.country,
  city = excluded.city,
  website = excluded.website,
  founded_year = excluded.founded_year,
  size_range = excluded.size_range,
  short_description = excluded.short_description;

-- Design studios
insert into firms (id, slug, display_name, canonical_name, sector, country, city, website, founded_year, size_range, short_description)
values
  ('a0000000-0000-0000-0000-000000000005', 'pentagram', 'Pentagram', 'pentagram', 'design', 'United Kingdom', 'London', 'https://www.pentagram.com', 1972, '200-500', 'Independent design consultancy with partner-led studios covering identity, digital, architecture, and product.'),
  ('a0000000-0000-0000-0000-000000000006', 'ideo', 'IDEO', 'ideo', 'design', 'United States', 'San Francisco', 'https://www.ideo.com', 1991, '500+', 'Global design and innovation firm pioneering human-centered design thinking methodology.')
on conflict (slug) do update set
  display_name = excluded.display_name,
  canonical_name = excluded.canonical_name,
  sector = excluded.sector,
  country = excluded.country,
  city = excluded.city,
  website = excluded.website,
  founded_year = excluded.founded_year,
  size_range = excluded.size_range,
  short_description = excluded.short_description;

-- Technology / research entities
insert into firms (id, slug, display_name, canonical_name, sector, country, city, website, founded_year, size_range, short_description)
values
  ('a0000000-0000-0000-0000-000000000007', 'mit-media-lab', 'MIT Media Lab', 'mit media lab', 'technology', 'United States', 'Cambridge', 'https://www.media.mit.edu', 1985, '50-200', 'Interdisciplinary research lab at MIT exploring technology, media, science, art, and design.'),
  ('a0000000-0000-0000-0000-000000000008', 'eth-zurich-dfab', 'ETH Zurich DFAB', 'eth zurich dfab', 'technology', 'Switzerland', 'Zurich', 'https://dfab.ch', 2016, '50-200', 'ETH research cluster focused on digital fabrication in architecture, combining robotics and computational design.'),
  ('a0000000-0000-0000-0000-000000000009', 'foster-and-partners', 'Foster + Partners', 'foster and partners', 'architecture', 'United Kingdom', 'London', 'https://www.fosterandpartners.com', 1967, '500+', 'International architecture and engineering practice led by Norman Foster, known for high-tech sustainable design.'),
  ('a0000000-0000-0000-0000-000000000010', 'the-living', 'The Living', 'the living', 'multidisciplinary', 'United States', 'New York', 'https://www.thelivingnewyork.com', 2005, '10-50', 'Autodesk studio exploring the intersection of biology, computation, and architecture.')
on conflict (slug) do update set
  display_name = excluded.display_name,
  canonical_name = excluded.canonical_name,
  sector = excluded.sector,
  country = excluded.country,
  city = excluded.city,
  website = excluded.website,
  founded_year = excluded.founded_year,
  size_range = excluded.size_range,
  short_description = excluded.short_description;

-- ============================================================
-- PEOPLE (8)
-- ============================================================

insert into people (id, slug, display_name, canonical_name, role, sector, current_firm_id, nationality, bio)
values
  ('b0000000-0000-0000-0000-000000000001', 'bjarke-ingels', 'Bjarke Ingels', 'bjarke ingels', 'Founding Partner', 'architecture', 'a0000000-0000-0000-0000-000000000001', 'Danish', 'Danish architect and founder of BIG. Known for "hedonistic sustainability" and ambitious urban projects.'),
  ('b0000000-0000-0000-0000-000000000002', 'winy-maas', 'Winy Maas', 'winy maas', 'Co-Founder', 'architecture', 'a0000000-0000-0000-0000-000000000002', 'Dutch', 'Dutch architect and co-founder of MVRDV. Professor at TU Delft, exploring density, data, and vertical cities.'),
  ('b0000000-0000-0000-0000-000000000003', 'patrik-schumacher', 'Patrik Schumacher', 'patrik schumacher', 'Principal', 'architecture', 'a0000000-0000-0000-0000-000000000003', 'German', 'Senior partner at Zaha Hadid Architects and theorist of parametricism in architecture.'),
  ('b0000000-0000-0000-0000-000000000004', 'norman-foster', 'Norman Foster', 'norman foster', 'Founder & Chairman', 'architecture', 'a0000000-0000-0000-0000-000000000009', 'British', 'British architect. Pritzker laureate. Pioneer of high-tech architecture and sustainable building design.'),
  ('b0000000-0000-0000-0000-000000000005', 'paula-scher', 'Paula Scher', 'paula scher', 'Partner', 'design', 'a0000000-0000-0000-0000-000000000005', 'American', 'Graphic designer and partner at Pentagram. Known for bold typographic identity work for major cultural institutions.'),
  ('b0000000-0000-0000-0000-000000000006', 'neri-oxman', 'Neri Oxman', 'neri oxman', 'Researcher', 'technology', null, 'Israeli-American', 'Designer and researcher known for material ecology, blending computation, biology, and material science in design.'),
  ('b0000000-0000-0000-0000-000000000007', 'craig-kielburger', 'Kjetil Trædal Thorsen', 'kjetil traedal thorsen', 'Co-Founder', 'architecture', 'a0000000-0000-0000-0000-000000000004', 'Norwegian', 'Norwegian architect and co-founder of Snøhetta. Led projects including the Oslo Opera House and Alexandria Library.'),
  ('b0000000-0000-0000-0000-000000000008', 'david-benjamin', 'David Benjamin', 'david benjamin', 'Director', 'multidisciplinary', 'a0000000-0000-0000-0000-000000000010', 'American', 'Architect, professor, and director of The Living at Autodesk. Explores computational design and biological materials.')
on conflict (slug) do update set
  display_name = excluded.display_name,
  canonical_name = excluded.canonical_name,
  role = excluded.role,
  sector = excluded.sector,
  current_firm_id = excluded.current_firm_id,
  nationality = excluded.nationality,
  bio = excluded.bio;

-- ============================================================
-- FIRM_PEOPLE (link existing people to firms)
-- ============================================================

insert into firm_people (firm_id, person_id, role, is_current)
values
  ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Founding Partner', true),
  ('a0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'Co-Founder', true),
  ('a0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000003', 'Principal', true),
  ('a0000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000004', 'Founder & Chairman', true),
  ('a0000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000005', 'Partner', true),
  ('a0000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000007', 'Co-Founder', true),
  ('a0000000-0000-0000-0000-000000000010', 'b0000000-0000-0000-0000-000000000008', 'Director', true)
on conflict (firm_id, person_id) do update set
  role = excluded.role,
  is_current = excluded.is_current;

-- ============================================================
-- AWARDS (4)
-- ============================================================

insert into awards (id, slug, award_name, organization, category, year, prestige)
values
  ('c0000000-0000-0000-0000-000000000001', 'pritzker-1999-norman-foster', 'Pritzker Architecture Prize', 'The Hyatt Foundation', 'Lifetime Achievement', 1999, '1'),
  ('c0000000-0000-0000-0000-000000000002', 'pritzker-2004-zaha-hadid', 'Pritzker Architecture Prize', 'The Hyatt Foundation', 'Lifetime Achievement', 2004, '1'),
  ('c0000000-0000-0000-0000-000000000003', 'waf-2023-big', 'World Architecture Festival Award', 'WAF', 'Building of the Year', 2023, '2'),
  ('c0000000-0000-0000-0000-000000000004', 'mies-van-der-rohe-2001-mvrdv', 'EU Mies Award', 'European Commission', 'Shortlist', 2001, '3')
on conflict (slug) do update set
  award_name = excluded.award_name,
  organization = excluded.organization,
  category = excluded.category,
  year = excluded.year,
  prestige = excluded.prestige;

-- ============================================================
-- AWARD_RECIPIENTS
-- ============================================================

insert into award_recipients (award_id, firm_id, person_id, year)
values
  ('c0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000004', 1999),
  ('c0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000003', null, 2004),
  ('c0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', null, 2023),
  ('c0000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000002', null, 2001)
on conflict (award_id, firm_id, person_id, year) do nothing;

-- ============================================================
-- SOURCES (3)
-- ============================================================

insert into sources (title, source_name, url, published_at, author, source_type, sector)
values
  ('BIG Unveils Masterplan for Oceanix Busan', 'ArchDaily', 'https://www.archdaily.com/example/big-oceanix-busan', '2024-06-15', 'Eric Baldwin', 'rss', 'architecture'),
  ('MVRDV Completes Markthal Rotterdam Renovation', 'Dezeen', 'https://www.dezeen.com/example/mvrdv-markthal', '2024-08-20', 'Tom Ravenscroft', 'rss', 'architecture'),
  ('Paula Scher Redesigns Public Theater Identity', 'It''s Nice That', 'https://www.itsnicethat.com/example/paula-scher-public-theater', '2024-03-10', null, 'rss', 'design')
on conflict (url) do nothing;

-- ============================================================
-- ENTITY ALIASES (sample)
-- ============================================================

insert into entity_aliases (entity_id, entity_type, alias, alias_normalized)
values
  ('a0000000-0000-0000-0000-000000000001', 'firm', 'BIG', 'big'),
  ('a0000000-0000-0000-0000-000000000001', 'firm', 'Bjarke Ingels Group', 'bjarke ingels group'),
  ('a0000000-0000-0000-0000-000000000003', 'firm', 'ZHA', 'zha'),
  ('a0000000-0000-0000-0000-000000000003', 'firm', 'Zaha Hadid ZHA Studio', 'zaha hadid zha studio'),
  ('a0000000-0000-0000-0000-000000000009', 'firm', 'Foster + Partners', 'foster and partners'),
  ('a0000000-0000-0000-0000-000000000009', 'firm', 'Foster Associates', 'foster associates')
on conflict (entity_type, alias_normalized) do nothing;
