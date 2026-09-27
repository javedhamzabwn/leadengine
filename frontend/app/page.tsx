"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, getFacets, getHealth } from "@/lib/api";
import type { Facets, Health } from "@/lib/types";

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: string;
  loading: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      {loading ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded bg-slate-100" />
      ) : (
        <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
      )}
    </div>
  );
}

function TopList({
  title,
  items,
  loading,
  empty,
}: {
  title: string;
  items: { value: string; count: number }[];
  loading: boolean;
  empty: string;
}) {
  const max = items.length > 0 ? items[0]!.count : 1;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      <div className="mt-3 space-y-2">
        {loading &&
          Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-5 animate-pulse rounded bg-slate-100"
            />
          ))}
        {!loading && items.length === 0 && (
          <p className="text-sm text-slate-400">{empty}</p>
        )}
        {!loading &&
          items.slice(0, 10).map((item) => (
            <div key={item.value} className="flex items-center gap-3">
              <span className="w-40 truncate text-sm text-slate-700" title={item.value}>
                {item.value}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded bg-slate-100">
                <div
                  className="h-full rounded bg-blue-500"
                  style={{ width: `${(item.count / max) * 100}%` }}
                />
              </div>
              <span className="w-16 text-right text-xs text-slate-500">
                {item.count.toLocaleString()}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [facets, setFacets] = useState<Facets | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, f] = await Promise.all([getHealth(), getFacets()]);
        if (!cancelled) {
          setHealth(h);
          setFacets(f);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError
              ? e.message
              : "Could not reach the API. Is the backend running?"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">
            Company dataset overview. All records are unverified, pre-scraped
            data.
          </p>
        </div>
        <Link
          href="/search"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Search companies
        </Link>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}{" "}
          <button
            className="ml-2 font-medium underline"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Companies"
          value={health ? health.db_rows.toLocaleString() : "-"}
          loading={loading}
        />
        <StatCard
          label="Industries tracked"
          value={facets ? facets.industries.length.toLocaleString() : "-"}
          loading={loading}
        />
        <StatCard
          label="Locations tracked"
          value={facets ? facets.locations.length.toLocaleString() : "-"}
          loading={loading}
        />
        <StatCard
          label="API status"
          value={health ? health.status : "-"}
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TopList
          title="Top industries"
          items={facets?.industries ?? []}
          loading={loading}
          empty="No industry data available."
        />
        <TopList
          title="Top locations"
          items={facets?.locations ?? []}
          loading={loading}
          empty="No location data available."
        />
        <TopList
          title="Operating status"
          items={facets?.operating_statuses ?? []}
          loading={loading}
          empty="No status data available."
        />
        <TopList
          title="Employee ranges"
          items={(facets?.employee_ranges ?? []).map((r) => ({
            value: r.label,
            count: r.count,
          }))}
          loading={loading}
          empty="No employee range data available."
        />
      </div>
    </div>
  );
}
