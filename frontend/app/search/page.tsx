"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  addFavorite,
  downloadExport,
  getFacets,
  listFavorites,
  removeFavorite,
  searchCompanies,
} from "@/lib/api";
import type {
  CompanyFilters,
  CompanySummary,
  ExportFormat,
  Facets,
  Paged,
} from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { FilterPanel } from "@/components/FilterPanel";
import { CompanyTable, ALL_COLUMNS } from "@/components/CompanyTable";
import { DetailDrawer } from "@/components/DetailDrawer";
import { SavedSearchesPanel } from "@/components/SavedSearchesPanel";
import { SORT_OPTIONS } from "@/lib/types";

const DEFAULT_FILTERS: CompanyFilters = {
  sort: "quality_score",
  dir: "desc",
  limit: 25,
};

const inputCls =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function SearchPage() {
  const { user } = useAuth();

  const [filters, setFilters] = useState<CompanyFilters>(DEFAULT_FILTERS);
  const [qInput, setQInput] = useState("");
  const [industryQuery, setIndustryQuery] = useState("");
  const [facets, setFacets] = useState<Facets | null>(null);
  const [facetsLoading, setFacetsLoading] = useState(true);

  const [items, setItems] = useState<CompanySummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  // Cursor used to fetch the current page, plus a stack of cursors for
  // previous pages so Prev navigation works without OFFSET.
  const [pageCursor, setPageCursor] = useState<string | null>(null);
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [columns, setColumns] = useState<string[]>(
    ALL_COLUMNS.map((c) => c.key)
  );
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [drawerId, setDrawerId] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("csv");
  const [exporting, setExporting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  // Debounce the keyword input (300ms)
  useEffect(() => {
    const t = setTimeout(() => {
      setFilters((prev) => {
        const q = qInput.trim();
        if ((prev.q ?? "") === q) return prev;
        return { ...prev, q: q || undefined };
      });
    }, 300);
    return () => clearTimeout(t);
  }, [qInput]);

  // Load facets once
  useEffect(() => {
    let cancelled = false;
    getFacets()
      .then((f) => {
        if (!cancelled) setFacets(f);
      })
      .catch(() => {
        /* facets are optional; filters still work */
      })
      .finally(() => {
        if (!cancelled) setFacetsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load favorite ids (first 500) so stars render correctly
  useEffect(() => {
    if (!user) {
      setFavorites(new Set());
      return;
    }
    let cancelled = false;
    (async () => {
      const ids = new Set<string>();
      let cursor: string | null = null;
      for (let i = 0; i < 20 && ids.size < 500; i++) {
        const page: Paged<CompanySummary> | null = await listFavorites(
          cursor
        ).catch(() => null);
        if (!page) break;
        for (const c of page.items) ids.add(c.id);
        cursor = page.next_cursor;
        if (!cursor) break;
      }
      if (!cancelled) setFavorites(ids);
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const fetchPage = useCallback(
    async (cursor: string | null, f: CompanyFilters) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setLoading(true);
      setError(null);
      try {
        const res = await searchCompanies(f, cursor, ctrl.signal);
        setItems(res.items);
        setNextCursor(res.next_cursor);
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(
          e instanceof ApiError
            ? e.message
            : "Search failed. Check that the API is running."
        );
        setItems([]);
        setNextCursor(null);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Any filter change resets pagination and refetches
  useEffect(() => {
    setCursorStack([]);
    setPageCursor(null);
    fetchPage(null, filters);
  }, [filters, fetchPage]);

  const patchFilters = (patch: Partial<CompanyFilters>) =>
    setFilters((prev) => ({ ...prev, ...patch }));

  const resetFilters = () => {
    setQInput("");
    setIndustryQuery("");
    setFilters(DEFAULT_FILTERS);
  };

  const goNext = () => {
    if (!nextCursor) return;
    setCursorStack((s) => [...s, pageCursor]);
    setPageCursor(nextCursor);
    fetchPage(nextCursor, filtersRef.current);
  };

  const goPrev = () => {
    if (cursorStack.length === 0) return;
    const prev = cursorStack[cursorStack.length - 1] ?? null;
    setCursorStack((s) => s.slice(0, -1));
    setPageCursor(prev);
    fetchPage(prev, filtersRef.current);
  };

  const toggleSelect = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const toggleSelectAll = () =>
    setSelected((prev) => {
      const next = new Set(prev);
      const allSelected = items.every((i) => next.has(i.id));
      for (const i of items) {
        if (allSelected) next.delete(i.id);
        else next.add(i.id);
      }
      return next;
    });

  const toggleFavorite = async (id: string) => {
    if (!user) {
      setNotice("Log in to save favorites.");
      return;
    }
    const isFav = favorites.has(id);
    // Optimistic update
    setFavorites((prev) => {
      const next = new Set(prev);
      if (isFav) next.delete(id);
      else next.add(id);
      return next;
    });
    try {
      if (isFav) await removeFavorite(id);
      else await addFavorite(id);
    } catch (e) {
      setFavorites((prev) => {
        const next = new Set(prev);
        if (isFav) next.add(id);
        else next.delete(id);
        return next;
      });
      setNotice(
        e instanceof ApiError ? e.message : "Could not update favorites."
      );
    }
  };

  const handleExport = async (onlySelected: boolean) => {
    const ids = onlySelected ? Array.from(selected) : undefined;
    if (onlySelected && ids!.length === 0) return;
    setExporting(true);
    setNotice(null);
    try {
      await downloadExport(filters, exportFormat, ids);
      setNotice(
        `Export started (${exportFormat.toUpperCase()}${
          onlySelected ? `, ${ids!.length} selected` : ", all matching"
        }).`
      );
    } catch (e) {
      setNotice(
        e instanceof ApiError ? e.message : "Export failed. Try again."
      );
    } finally {
      setExporting(false);
    }
  };

  const pageNumber = cursorStack.length + 1;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Company search</h1>
        <p className="text-sm text-slate-500">
          Search the company dataset. All records are unverified, pre-scraped
          data.
        </p>
      </div>

      {notice && (
        <div className="flex items-center justify-between rounded-md border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm text-blue-800">
          <span>{notice}</span>
          <button
            onClick={() => setNotice(null)}
            className="ml-4 font-medium underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span>{error}</span>
          <button
            onClick={() => fetchPage(null, filtersRef.current)}
            className="ml-4 shrink-0 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )}

      <div className="flex gap-4">
        {/* Filters sidebar */}
        <aside
          className={`${
            filtersOpen ? "block" : "hidden"
          } w-64 shrink-0 lg:block`}
        >
          <div className="space-y-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <FilterPanel
              filters={filters}
              facets={facets}
              facetsLoading={facetsLoading}
              onChange={patchFilters}
              onReset={resetFilters}
              industryQuery={industryQuery}
              onIndustryQueryChange={setIndustryQuery}
            />
            <div className="border-t border-slate-200 pt-4">
              <SavedSearchesPanel
                currentFilters={filters}
                onLoad={(f) => {
                  setQInput(f.q ?? "");
                  setFilters({ ...DEFAULT_FILTERS, ...f });
                }}
              />
            </div>
          </div>
        </aside>

        {/* Main column */}
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 lg:hidden"
              onClick={() => setFiltersOpen((v) => !v)}
            >
              {filtersOpen ? "Hide filters" : "Show filters"}
            </button>
            <input
              className={`${inputCls} flex-1 min-w-48`}
              placeholder="Search companies (min 2 characters)..."
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
            />
            <select
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={filters.sort ?? "quality_score"}
              onChange={(e) =>
                patchFilters({
                  sort: e.target.value,
                  dir: e.target.value === "name" ? "asc" : "desc",
                })
              }
              aria-label="Sort by"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  Sort: {o.label}
                </option>
              ))}
            </select>
            <button
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700"
              onClick={() =>
                patchFilters({ dir: filters.dir === "asc" ? "desc" : "asc" })
              }
              aria-label="Toggle sort direction"
              title="Toggle sort direction"
            >
              {filters.dir === "asc" ? "↑ Asc" : "↓ Desc"}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-500">
              {selected.size} selected
            </span>
            <select
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
              aria-label="Export format"
            >
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
              <option value="xlsx">XLSX</option>
            </select>
            <button
              disabled={selected.size === 0 || exporting}
              onClick={() => handleExport(true)}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {exporting ? "Exporting..." : `Export selected (${selected.size})`}
            </button>
            <button
              disabled={exporting}
              onClick={() => handleExport(false)}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Export all matching
            </button>
          </div>

          <CompanyTable
            items={items}
            columns={columns}
            sort={filters.sort ?? "quality_score"}
            dir={filters.dir ?? "desc"}
            selected={selected}
            favorites={favorites}
            loading={loading}
            onSortChange={(sort, dir) => patchFilters({ sort, dir })}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onToggleFavorite={toggleFavorite}
            onRowClick={(id) => setDrawerId(id)}
            onColumnsChange={setColumns}
          />

          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Page {pageNumber}</p>
            <div className="flex gap-2">
              <button
                disabled={cursorStack.length === 0 || loading}
                onClick={goPrev}
                className="rounded-md border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={!nextCursor || loading}
                onClick={goNext}
                className="rounded-md border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>

      <DetailDrawer companyId={drawerId} onClose={() => setDrawerId(null)} />
    </div>
  );
}
