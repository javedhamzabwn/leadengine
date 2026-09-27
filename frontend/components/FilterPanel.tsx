"use client";

import { useMemo } from "react";
import type { CompanyFilters, Facets } from "@/lib/types";

interface Props {
  filters: CompanyFilters;
  facets: Facets | null;
  facetsLoading: boolean;
  onChange: (patch: Partial<CompanyFilters>) => void;
  onReset: () => void;
  industryQuery: string;
  onIndustryQueryChange: (q: string) => void;
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between text-sm text-slate-700">
      {label}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition-colors ${
          checked ? "bg-blue-600" : "bg-slate-300"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
  );
}

const inputCls =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export function FilterPanel({
  filters,
  facets,
  facetsLoading,
  onChange,
  onReset,
  industryQuery,
  onIndustryQueryChange,
}: Props) {
  const visibleIndustries = useMemo(() => {
    const list = facets?.industries ?? [];
    const q = industryQuery.trim().toLowerCase();
    const filtered = q
      ? list.filter((i) => i.value.toLowerCase().includes(q))
      : list;
    return filtered.slice(0, 20);
  }, [facets, industryQuery]);

  const toggleIndustry = (value: string) => {
    const current = filters.industry ?? [];
    onChange({
      industry: current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value],
    });
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Filters
        </h2>
        <button
          onClick={onReset}
          className="text-xs font-medium text-blue-600 hover:text-blue-800"
        >
          Reset all
        </button>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">
          Location
        </label>
        <input
          className={inputCls}
          placeholder="City, region or country"
          value={filters.location ?? ""}
          onChange={(e) => onChange({ location: e.target.value })}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">
          Industry
        </label>
        <input
          className={`${inputCls} mb-2`}
          placeholder="Filter industries..."
          value={industryQuery}
          onChange={(e) => onIndustryQueryChange(e.target.value)}
        />
        <div className="max-h-48 space-y-1 overflow-y-auto pr-1">
          {facetsLoading && (
            <p className="text-xs text-slate-400">Loading industries...</p>
          )}
          {!facetsLoading &&
            visibleIndustries.map((item) => (
              <label
                key={item.value}
                className="flex cursor-pointer items-center gap-2 text-sm text-slate-700"
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-blue-600"
                  checked={(filters.industry ?? []).includes(item.value)}
                  onChange={() => toggleIndustry(item.value)}
                />
                <span className="flex-1 truncate" title={item.value}>
                  {item.value}
                </span>
                <span className="text-xs text-slate-400">
                  {item.count.toLocaleString()}
                </span>
              </label>
            ))}
          {!facetsLoading && visibleIndustries.length === 0 && (
            <p className="text-xs text-slate-400">No industries found.</p>
          )}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">
          Employee range
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            min={0}
            className={inputCls}
            placeholder="Min"
            value={filters.employees_min ?? ""}
            onChange={(e) =>
              onChange({
                employees_min: e.target.value
                  ? Number(e.target.value)
                  : undefined,
              })
            }
          />
          <input
            type="number"
            min={0}
            className={inputCls}
            placeholder="Max"
            value={filters.employees_max ?? ""}
            onChange={(e) =>
              onChange({
                employees_max: e.target.value
                  ? Number(e.target.value)
                  : undefined,
              })
            }
          />
        </div>
        {facets && facets.employee_ranges.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {facets.employee_ranges.slice(0, 6).map((r) => (
              <span
                key={r.value}
                title={`${r.count.toLocaleString()} companies`}
                className="rounded-full border border-slate-200 px-2 py-0.5 text-xs text-slate-500"
              >
                {r.label}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2">
        <Toggle
          label="Has email"
          checked={filters.has_email === true}
          onChange={(v) => onChange({ has_email: v || undefined })}
        />
        <Toggle
          label="Has phone"
          checked={filters.has_phone === true}
          onChange={(v) => onChange({ has_phone: v || undefined })}
        />
        <Toggle
          label="Has LinkedIn"
          checked={filters.has_linkedin === true}
          onChange={(v) => onChange({ has_linkedin: v || undefined })}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">
          Minimum quality score:{" "}
          {filters.min_quality !== undefined
            ? filters.min_quality.toFixed(2)
            : "any"}
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          className="w-full"
          value={filters.min_quality ?? 0}
          onChange={(e) => {
            const v = Number(e.target.value);
            onChange({ min_quality: v > 0 ? v : undefined });
          }}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">
          Operating status
        </label>
        <select
          className={inputCls}
          value={filters.operating_status ?? ""}
          onChange={(e) =>
            onChange({ operating_status: e.target.value || undefined })
          }
        >
          <option value="">Any status</option>
          {(facets?.operating_statuses ?? []).map((s) => (
            <option key={s.value} value={s.value}>
              {s.value} ({s.count.toLocaleString()})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
