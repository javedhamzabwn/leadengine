"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  createSavedSearch,
  deleteSavedSearch,
  listSavedSearches,
} from "@/lib/api";
import type { CompanyFilters, SavedSearch } from "@/lib/types";
import { useAuth } from "@/lib/auth";

interface Props {
  currentFilters: CompanyFilters;
  onLoad: (filters: CompanyFilters) => void;
}

export function SavedSearchesPanel({ currentFilters, onLoad }: Props) {
  const { user } = useAuth();
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    if (!user) {
      setSearches([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { items } = await listSavedSearches();
      setSearches(items);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Failed to load saved searches"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleSave = async () => {
    const trimmed = name.trim();
    if (!trimmed || saving) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await createSavedSearch({
        name: trimmed,
        filters: currentFilters,
      });
      setSearches((prev) => [saved, ...prev]);
      setName("");
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Failed to save search"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSavedSearch(id);
      setSearches((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Failed to delete saved search"
      );
    }
  };

  if (!user) {
    return (
      <p className="text-xs text-slate-400">
        Log in to save and reuse searches.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Saved searches
      </h2>
      <div className="flex gap-2">
        <input
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Name this search..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
          }}
        />
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="shrink-0 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {loading ? (
        <p className="text-xs text-slate-400">Loading...</p>
      ) : searches.length === 0 ? (
        <p className="text-xs text-slate-400">
          No saved searches yet. Apply filters above, then save them here.
        </p>
      ) : (
        <ul className="space-y-1">
          {searches.map((s) => (
            <li
              key={s.id}
              className="group flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-slate-100"
            >
              <button
                onClick={() => onLoad(s.filters)}
                className="min-w-0 flex-1 truncate text-left text-sm font-medium text-slate-700 hover:text-blue-700"
                title="Load this search"
              >
                {s.name}
              </button>
              <button
                onClick={() => handleDelete(s.id)}
                aria-label={`Delete saved search ${s.name}`}
                className="text-xs text-slate-400 hover:text-red-600"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
