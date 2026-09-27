// Typed API client for the LeadEngine contract (SPECS/API_CONTRACT.md).
// Base URL from NEXT_PUBLIC_API_URL, default http://127.0.0.1:8000.
// Throws ApiError on contract { error: { code, message } } bodies.

import type {
  CompanyDetail,
  CompanyFilters,
  CompanySummary,
  ExportFormat,
  Facets,
  FavoriteEntry,
  Health,
  Paged,
  SavedSearch,
  User,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

// Token provider is injected by the auth module so this client stays
// framework-agnostic. Defaults to localStorage lookup in the browser.
let tokenProvider: () => string | null = () =>
  typeof window !== "undefined"
    ? window.localStorage.getItem("leadengine_token")
    : null;

export function setTokenProvider(fn: () => string | null) {
  tokenProvider = fn;
}

function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = new URL(API_BASE + path);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      if (Array.isArray(value)) {
        for (const v of value) url.searchParams.append(key, String(v));
      } else {
        url.searchParams.append(key, String(value));
      }
    }
  }
  return url.toString();
}

// Bypass header for free tunnel services (e.g. localtunnel) that show a
// browser reminder interstitial. Only sent when the API is behind a
// known tunnel host; unknown headers are ignored by other servers.
function tunnelBypassHeaders(): Record<string, string> {
  return API_BASE.includes(".loca.lt") ? { "bypass-tunnel-reminder": "1" } : {};
}

async function request<T>(
  path: string,
  opts: {
    method?: string;
    params?: Record<string, unknown>;
    body?: unknown;
    auth?: boolean;
  } = {}
): Promise<T> {
  const headers: Record<string, string> = { ...tunnelBypassHeaders() };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.auth !== false) {
    const token = tokenProvider();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.params), {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch (e) {
    throw new ApiError(
      "network_error",
      e instanceof Error ? e.message : "Network request failed",
      0
    );
  }

  const contentType = res.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    const err = data && typeof data === "object" && "error" in data
      ? (data as { error: { code?: string; message?: string; details?: unknown } }).error
      : null;
    throw new ApiError(
      err?.code ?? `http_${res.status}`,
      err?.message ?? `Request failed with status ${res.status}`,
      res.status,
      err?.details
    );
  }
  return data as T;
}

export function filtersToParams(
  f: CompanyFilters
): Record<string, unknown> {
  return {
    q: f.q && f.q.length >= 2 ? f.q : undefined,
    industry: f.industry && f.industry.length > 0 ? f.industry : undefined,
    location: f.location || undefined,
    employees_min: f.employees_min,
    employees_max: f.employees_max,
    has_email: f.has_email === true ? true : undefined,
    has_phone: f.has_phone === true ? true : undefined,
    has_linkedin: f.has_linkedin === true ? true : undefined,
    min_quality: f.min_quality,
    operating_status: f.operating_status || undefined,
    sort: f.sort,
    dir: f.dir,
    limit: f.limit,
  };
}

// ---------------------------------------------------------------------------
// Health / misc
// ---------------------------------------------------------------------------

export function getHealth(): Promise<Health> {
  return request<Health>("/health", { auth: false });
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export function signup(input: {
  email: string;
  password: string;
  name: string;
}): Promise<{ user: User }> {
  return request<{ user: User }>("/api/v1/auth/signup", {
    method: "POST",
    body: input,
    auth: false,
  });
}

export function login(input: {
  email: string;
  password: string;
}): Promise<{ token: string; user: User }> {
  return request<{ token: string; user: User }>("/api/v1/auth/login", {
    method: "POST",
    body: input,
    auth: false,
  });
}

export function me(): Promise<{ user: User }> {
  return request<{ user: User }>("/api/v1/auth/me");
}

// ---------------------------------------------------------------------------
// Companies
// ---------------------------------------------------------------------------

export function searchCompanies(
  filters: CompanyFilters,
  cursor?: string | null,
  signal?: AbortSignal
): Promise<Paged<CompanySummary>> {
  const url = buildUrl("/api/v1/companies", {
    ...filtersToParams(filters),
    cursor: cursor || undefined,
  });
  return authedFetch<Paged<CompanySummary>>(url, signal);
}

async function authedFetch<T>(url: string, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = { ...tunnelBypassHeaders() };
  const token = tokenProvider();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(url, { headers, signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(
      "network_error",
      e instanceof Error ? e.message : "Network request failed",
      0
    );
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err =
      data && typeof data === "object" && "error" in data
        ? (data as { error: { code?: string; message?: string } }).error
        : null;
    throw new ApiError(
      err?.code ?? `http_${res.status}`,
      err?.message ?? `Request failed with status ${res.status}`,
      res.status
    );
  }
  return data as T;
}

export function getCompany(id: string): Promise<CompanyDetail> {
  return request<CompanyDetail>(
    `/api/v1/companies/${encodeURIComponent(id)}`
  );
}

export function getFacets(): Promise<Facets> {
  return request<Facets>("/api/v1/companies/facets");
}

// Export URL builder for the filter-based export. The contract defines
// GET /api/v1/companies/export with the same filters + format. Bulk export of
// selected ids is NOT supported on the GET route (it exports by filters only);
// use downloadExport, which POSTs {ids, format} to /api/v1/companies/export.
export function exportUrl(
  filters: CompanyFilters,
  format: ExportFormat
): string {
  return buildUrl("/api/v1/companies/export", {
    ...filtersToParams(filters),
    format,
  });
}

export async function downloadExport(
  filters: CompanyFilters,
  format: ExportFormat,
  ids?: string[]
): Promise<void> {
  const headers: Record<string, string> = { ...tunnelBypassHeaders() };
  const token = tokenProvider();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  // Selection export: POST /api/v1/companies/export {ids, format}.
  // (GET /api/v1/companies/export ignores ids and exports by filters, so a
  // selection export over GET would return the wrong rows or export_too_large.)
  const res =
    ids && ids.length > 0
      ? await fetch(API_BASE + "/api/v1/companies/export", {
          method: "POST",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify({ ids, format }),
        })
      : await fetch(exportUrl(filters, format), { headers });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const err =
      data && typeof data === "object" && "error" in data
        ? (data as { error: { code?: string; message?: string } }).error
        : null;
    throw new ApiError(
      err?.code ?? `http_${res.status}`,
      err?.message ?? `Export failed with status ${res.status}`,
      res.status
    );
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = /filename="?([^";]+)"?/.exec(disposition);
  const filename =
    match?.[1] ?? `leadengine-export-${Date.now()}.${format}`;
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);
}

// ---------------------------------------------------------------------------
// Saved searches
// ---------------------------------------------------------------------------

export function listSavedSearches(): Promise<{ items: SavedSearch[] }> {
  return request<{ items: SavedSearch[] }>("/api/v1/saved-searches");
}

export function createSavedSearch(input: {
  name: string;
  filters: CompanyFilters;
}): Promise<SavedSearch> {
  return request<SavedSearch>("/api/v1/saved-searches", {
    method: "POST",
    body: input,
  });
}

export function deleteSavedSearch(id: string): Promise<void> {
  return request<void>(`/api/v1/saved-searches/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Favorites
// ---------------------------------------------------------------------------

export function addFavorite(companyId: string): Promise<FavoriteEntry> {
  return request<FavoriteEntry>(
    `/api/v1/companies/${encodeURIComponent(companyId)}/favorites`,
    { method: "POST" }
  );
}

export function removeFavorite(companyId: string): Promise<void> {
  return request<void>(
    `/api/v1/companies/${encodeURIComponent(companyId)}/favorites`,
    { method: "DELETE" }
  );
}

export function listFavorites(
  cursor?: string | null
): Promise<Paged<CompanySummary>> {
  return request<Paged<CompanySummary>>("/api/v1/favorites", {
    params: { cursor: cursor || undefined, limit: 25 },
  });
}
