"use client";

import { useEffect, useState } from "react";
import { ApiError, getCompany } from "@/lib/api";
import type { CompanyDetail } from "@/lib/types";

interface Props {
  companyId: string | null;
  onClose: () => void;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm text-slate-900">{value ?? "-"}</dd>
    </div>
  );
}

export function DetailDrawer({ companyId, onClose }: Props) {
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId) {
      setCompany(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getCompany(companyId)
      .then((c) => {
        if (!cancelled) setCompany(c);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof ApiError ? e.message : "Failed to load company details"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!companyId) return null;

  return (
    <div className="fixed inset-0 z-40">
      <div
        className="absolute inset-0 bg-slate-900/40"
        onClick={onClose}
        aria-hidden
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-lg flex-col bg-white shadow-xl">
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-slate-900">
              {company?.name ?? "Company details"}
            </h2>
            {company?.domain && (
              <p className="text-sm text-slate-500">{company.domain}</p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close details"
            className="rounded-md p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="h-6 animate-pulse rounded bg-slate-100"
                />
              ))}
            </div>
          )}
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          )}
          {company && !loading && (
            <div className="space-y-6">
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                <p className="text-sm font-semibold text-amber-900">
                  Fit score (unverified data):{" "}
                  {company.lead_score !== null
                    ? `${Math.round(company.lead_score * 100)}%`
                    : "not computed"}
                </p>
                <p className="mt-0.5 text-xs text-amber-800">
                  This score is computed from unverified, pre-scraped data.
                  It is not verified intent.
                </p>
                {company.score_signals && company.score_signals.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {company.score_signals.map((s, i) => (
                      <li
                        key={i}
                        className="flex items-start justify-between gap-2 text-xs text-amber-900"
                      >
                        <span>
                          {s.signal}
                          {s.detail ? ` (${s.detail})` : ""}
                        </span>
                        <span className="font-semibold">
                          +{Math.round(s.points * 100)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <dl className="grid grid-cols-2 gap-4">
                <Field label="Industry" value={company.industry} />
                <Field label="Location" value={company.hq_location} />
                <Field
                  label="Employees"
                  value={
                    company.employee_enum ??
                    (company.employees_min !== null
                      ? `${company.employees_min.toLocaleString()} - ${(
                          company.employees_max ?? "?"
                        ).toLocaleString()}`
                      : null)
                  }
                />
                <Field label="Founded" value={company.founded_year} />
                <Field
                  label="Operating status"
                  value={company.operating_status}
                />
                <Field
                  label="Quality score"
                  value={
                    company.quality_score !== null
                      ? `${Math.round(company.quality_score * 100)}%`
                      : null
                  }
                />
                <Field
                  label="Verification"
                  value={company.verification_status}
                />
                <Field label="Website" value={company.website} />
              </dl>

              {company.description && (
                <div>
                  <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Description
                  </h3>
                  <p className="text-sm text-slate-800">
                    {company.description}
                  </p>
                </div>
              )}

              <div>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Contact
                </h3>
                <dl className="grid grid-cols-2 gap-4">
                  <Field label="Email" value={company.email} />
                  <Field
                    label="Email valid"
                    value={
                      company.email_valid === null
                        ? null
                        : company.email_valid
                          ? "yes"
                          : "no"
                    }
                  />
                  <Field label="Phone" value={company.phone} />
                  <Field label="LinkedIn" value={company.linkedin} />
                  <Field label="Twitter" value={company.twitter} />
                  <Field label="Facebook" value={company.facebook} />
                </dl>
              </div>

              <div>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Funding
                </h3>
                <dl className="grid grid-cols-2 gap-4">
                  <Field
                    label="Total funding"
                    value={
                      company.funding_total_usd !== null
                        ? `$${company.funding_total_usd.toLocaleString()}`
                        : null
                    }
                  />
                  <Field
                    label="Funding rounds"
                    value={company.funding_rounds}
                  />
                  <Field
                    label="Last funding type"
                    value={company.last_funding_type}
                  />
                  <Field
                    label="Crunchbase"
                    value={company.crunchbase_url}
                  />
                </dl>
              </div>

              <div>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Provenance
                </h3>
                <dl className="grid grid-cols-2 gap-4">
                  <Field label="Source" value={company.source} />
                  <Field label="Observed at" value={company.observed_at} />
                </dl>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
