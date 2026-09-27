"use client";

import type { CompanySummary } from "@/lib/types";

export interface ColumnDef {
  key: string;
  label: string;
}

export const ALL_COLUMNS: ColumnDef[] = [
  { key: "name", label: "Company" },
  { key: "industry", label: "Industry" },
  { key: "hq_location", label: "Location" },
  { key: "employees", label: "Employees" },
  { key: "founded_year", label: "Founded" },
  { key: "quality_score", label: "Quality" },
  { key: "lead_score", label: "Fit score" },
  { key: "contacts", label: "Contacts" },
];

interface Props {
  items: CompanySummary[];
  columns: string[];
  sort: string;
  dir: "asc" | "desc";
  selected: Set<string>;
  favorites: Set<string>;
  loading: boolean;
  onSortChange: (sort: string, dir: "asc" | "desc") => void;
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  onToggleFavorite: (id: string) => void;
  onRowClick: (id: string) => void;
  onColumnsChange: (columns: string[]) => void;
}

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "-";
  return `${Math.round(v * 100)}%`;
}

const SORTABLE: Record<string, string> = {
  name: "name",
  quality_score: "quality_score",
  employees: "employees_max",
  founded_year: "founded_year",
};

export function CompanyTable({
  items,
  columns,
  sort,
  dir,
  selected,
  favorites,
  loading,
  onSortChange,
  onToggleSelect,
  onToggleSelectAll,
  onToggleFavorite,
  onRowClick,
  onColumnsChange,
}: Props) {
  const allSelected = items.length > 0 && items.every((i) => selected.has(i.id));

  const handleHeaderClick = (colKey: string) => {
    const sortField = SORTABLE[colKey];
    if (!sortField) return;
    if (sort === sortField) {
      onSortChange(sortField, dir === "asc" ? "desc" : "asc");
    } else {
      onSortChange(sortField, sortField === "name" ? "asc" : "desc");
    }
  };

  const toggleColumn = (key: string) => {
    if (columns.includes(key)) {
      if (columns.length > 1) onColumnsChange(columns.filter((c) => c !== key));
    } else {
      onColumnsChange([...columns, key]);
    }
  };

  const renderCell = (company: CompanySummary, colKey: string) => {
    switch (colKey) {
      case "name":
        return (
          <div className="min-w-0">
            <div className="truncate font-medium text-slate-900">
              {company.name}
            </div>
            {company.domain && (
              <div className="truncate text-xs text-slate-500">
                {company.domain}
              </div>
            )}
          </div>
        );
      case "industry":
        return (
          <span className="text-sm text-slate-700">
            {company.industry ?? "-"}
          </span>
        );
      case "hq_location":
        return (
          <span className="text-sm text-slate-700">
            {company.hq_location ?? "-"}
          </span>
        );
      case "employees":
        return (
          <span className="text-sm text-slate-700">
            {company.employee_enum ??
              (company.employees_min !== null &&
              company.employees_max !== null
                ? `${company.employees_min.toLocaleString()}-${company.employees_max.toLocaleString()}`
                : "-")}
          </span>
        );
      case "founded_year":
        return (
          <span className="text-sm text-slate-700">
            {company.founded_year ?? "-"}
          </span>
        );
      case "quality_score":
        return (
          <span className="text-sm font-medium text-slate-700">
            {pct(company.quality_score)}
          </span>
        );
      case "lead_score":
        return (
          <span className="text-sm font-medium text-blue-700">
            {pct(company.lead_score)}
          </span>
        );
      case "contacts":
        return (
          <div className="flex gap-1">
            {company.has_email && (
              <span
                title="Has email"
                className="rounded bg-emerald-50 px-1.5 py-0.5 text-xs font-medium text-emerald-700"
              >
                email
              </span>
            )}
            {company.has_phone && (
              <span
                title="Has phone"
                className="rounded bg-sky-50 px-1.5 py-0.5 text-xs font-medium text-sky-700"
              >
                phone
              </span>
            )}
            {company.has_linkedin && (
              <span
                title="Has LinkedIn"
                className="rounded bg-indigo-50 px-1.5 py-0.5 text-xs font-medium text-indigo-700"
              >
                in
              </span>
            )}
            {!company.has_email && !company.has_phone && !company.has_linkedin && (
              <span className="text-xs text-slate-400">-</span>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-500">Columns:</span>
        {ALL_COLUMNS.map((col) => (
          <label
            key={col.key}
            className="flex cursor-pointer items-center gap-1 rounded-full border border-slate-200 px-2 py-0.5 text-xs text-slate-600"
          >
            <input
              type="checkbox"
              className="h-3 w-3 rounded border-slate-300 text-blue-600"
              checked={columns.includes(col.key)}
              onChange={() => toggleColumn(col.key)}
            />
            {col.label}
          </label>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="w-10 px-3 py-2.5">
                <input
                  type="checkbox"
                  aria-label="Select all rows on this page"
                  className="h-4 w-4 rounded border-slate-300 text-blue-600"
                  checked={allSelected}
                  onChange={onToggleSelectAll}
                />
              </th>
              <th className="w-10 px-2 py-2.5" aria-label="Favorite" />
              {ALL_COLUMNS.filter((c) => columns.includes(c.key)).map((col) => {
                const sortField = SORTABLE[col.key];
                const active = sortField && sort === sortField;
                return (
                  <th
                    key={col.key}
                    className={`px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 ${
                      sortField ? "cursor-pointer select-none hover:text-slate-800" : ""
                    }`}
                    onClick={() => handleHeaderClick(col.key)}
                  >
                    {col.label}
                    {sortField && (
                      <span className="ml-1 text-slate-400">
                        {active ? (dir === "asc" ? "▲" : "▼") : "△"}
                      </span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={`skeleton-${i}`} className="animate-pulse">
                  <td colSpan={columns.length + 2} className="px-3 py-3">
                    <div className="h-5 rounded bg-slate-100" />
                  </td>
                </tr>
              ))}
            {!loading &&
              items.map((company) => (
                <tr
                  key={company.id}
                  className={`cursor-pointer hover:bg-blue-50/50 ${
                    selected.has(company.id) ? "bg-blue-50" : ""
                  }`}
                  onClick={() => onRowClick(company.id)}
                >
                  <td
                    className="px-3 py-2.5"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      aria-label={`Select ${company.name}`}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600"
                      checked={selected.has(company.id)}
                      onChange={() => onToggleSelect(company.id)}
                    />
                  </td>
                  <td
                    className="px-2 py-2.5"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      aria-label={
                        favorites.has(company.id)
                          ? `Remove ${company.name} from favorites`
                          : `Add ${company.name} to favorites`
                      }
                      onClick={() => onToggleFavorite(company.id)}
                      className={`text-lg leading-none ${
                        favorites.has(company.id)
                          ? "text-amber-400"
                          : "text-slate-300 hover:text-amber-300"
                      }`}
                    >
                      ★
                    </button>
                  </td>
                  {ALL_COLUMNS.filter((c) => columns.includes(c.key)).map(
                    (col) => (
                      <td key={col.key} className="whitespace-nowrap px-3 py-2.5">
                        {renderCell(company, col.key)}
                      </td>
                    )
                  )}
                </tr>
              ))}
          </tbody>
        </table>
        {!loading && items.length === 0 && (
          <div className="px-4 py-12 text-center">
            <p className="text-sm font-medium text-slate-700">
              No companies match your filters.
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Try widening the filters or clearing the search term.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
