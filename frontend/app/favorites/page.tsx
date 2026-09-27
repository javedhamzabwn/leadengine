"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, listFavorites, removeFavorite } from "@/lib/api";
import type { CompanySummary } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { CompanyTable, ALL_COLUMNS } from "@/components/CompanyTable";
import { DetailDrawer } from "@/components/DetailDrawer";

export default function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<CompanySummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [columns, setColumns] = useState<string[]>(
    ALL_COLUMNS.map((c) => c.key)
  );
  const [drawerId, setDrawerId] = useState<string | null>(null);

  const fetchFirst = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listFavorites(null);
      setItems(page.items);
      setNextCursor(page.next_cursor);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Failed to load favorites."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && user) fetchFirst();
    if (!authLoading && !user) setLoading(false);
  }, [authLoading, user, fetchFirst]);

  const loadMore = async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await listFavorites(nextCursor);
      setItems((prev) => [...prev, ...page.items]);
      setNextCursor(page.next_cursor);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Failed to load more favorites."
      );
    } finally {
      setLoadingMore(false);
    }
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

  const remove = async (id: string) => {
    try {
      await removeFavorite(id);
      setItems((prev) => prev.filter((c) => c.id !== id));
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Could not remove favorite."
      );
    }
  };

  const favoriteIds = new Set(items.map((c) => c.id));

  if (!authLoading && !user) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-xl font-bold text-slate-900">Favorites</h1>
        <p className="mt-2 text-sm text-slate-500">
          Log in to see the companies you starred.
        </p>
        <Link
          href="/login"
          className="mt-4 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Log in
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Favorites</h1>
        <p className="text-sm text-slate-500">
          Companies you starred. Click a row for details.
        </p>
      </div>

      {error && (
        <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span>{error}</span>
          <button
            onClick={fetchFirst}
            className="ml-4 shrink-0 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )}

      <CompanyTable
        items={items}
        columns={columns}
        sort="quality_score"
        dir="desc"
        selected={selected}
        favorites={favoriteIds}
        loading={loading}
        onSortChange={() => {}}
        onToggleSelect={toggleSelect}
        onToggleSelectAll={toggleSelectAll}
        onToggleFavorite={remove}
        onRowClick={(id) => setDrawerId(id)}
        onColumnsChange={setColumns}
      />

      {nextCursor && (
        <div className="text-center">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {loadingMore ? "Loading..." : "Load more"}
          </button>
        </div>
      )}

      {!loading && items.length === 0 && !error && (
        <p className="text-sm text-slate-500">
          No favorites yet. Star companies from the{" "}
          <Link href="/search" className="text-blue-600 hover:underline">
            search page
          </Link>
          .
        </p>
      )}

      <DetailDrawer companyId={drawerId} onClose={() => setDrawerId(null)} />
    </div>
  );
}
