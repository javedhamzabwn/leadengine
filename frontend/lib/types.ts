// Shared types matching SPECS/API_CONTRACT.md

export interface User {
  id: string;
  email: string;
  name: string;
  org_id: string | null;
  role: string;
  created_at: string;
}

export interface CompanySummary {
  id: string;
  name: string;
  domain: string | null;
  website: string | null;
  industry: string | null;
  hq_location: string | null;
  employee_enum: string | null;
  employees_min: number | null;
  employees_max: number | null;
  founded_year: number | null;
  operating_status: string | null;
  has_email: boolean;
  has_phone: boolean;
  has_linkedin: boolean;
  quality_score: number | null;
  lead_score: number | null;
  verification_status: string;
}

export interface ScoreSignal {
  signal: string;
  points: number;
  detail: string;
}

export interface CompanyDetail extends CompanySummary {
  description: string | null;
  email: string | null;
  email_valid: boolean | null;
  phone: string | null;
  facebook: string | null;
  linkedin: string | null;
  twitter: string | null;
  industries: string[] | null;
  locations_raw: string | null;
  location_tail: string | null;
  funding_total_usd: number | null;
  funding_rounds: number | null;
  last_funding_type: string | null;
  last_funding_at: string | null;
  founded_on: string | null;
  company_type: string | null;
  ipo_status: string | null;
  crunchbase_url: string | null;
  score_signals: ScoreSignal[];
  source: string | null;
  observed_at: string | null;
}

export interface FacetItem {
  value: string;
  count: number;
}

export interface EmployeeRangeFacet {
  value: string;
  label: string;
  count: number;
}

export interface Facets {
  industries: FacetItem[];
  locations: FacetItem[];
  operating_statuses: FacetItem[];
  employee_ranges: EmployeeRangeFacet[];
}

export interface Paged<T> {
  items: T[];
  next_cursor: string | null;
  limit: number;
}

export interface Health {
  status: string;
  service: string;
  version: string;
  db_rows: number;
}

export interface CompanyFilters {
  q?: string;
  industry?: string[];
  location?: string;
  employees_min?: number;
  employees_max?: number;
  has_email?: boolean;
  has_phone?: boolean;
  has_linkedin?: boolean;
  min_quality?: number;
  operating_status?: string;
  sort?: string;
  dir?: "asc" | "desc";
  limit?: number;
}

export interface SavedSearch {
  id: string;
  name: string;
  filters: CompanyFilters;
  created_at: string;
}

export interface FavoriteEntry {
  company_id: string;
  created_at: string;
}

export const SORT_OPTIONS = [
  { value: "quality_score", label: "Quality score" },
  { value: "name", label: "Name" },
  { value: "employees_max", label: "Company size" },
  { value: "founded_year", label: "Founded year" },
] as const;

export const EXPORT_FORMATS = ["csv", "json", "xlsx"] as const;
export type ExportFormat = (typeof EXPORT_FORMATS)[number];
