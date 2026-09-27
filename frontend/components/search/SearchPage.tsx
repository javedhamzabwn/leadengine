// SearchPage — minimal integration with backend search_service.py
// Uses fetch to FastAPI /search endpoint; no state management libs required

import { useEffect, useState } from 'react'

interface SearchResult {
  id: string
  full_name: string
  current_title: string
  current_company: string
  department: string
  seniority: string
  location: string
  industry: string
  linkedin_url: string
}

interface SearchFilters {
  department?: string
  title?: string
  seniority?: string
  location?: string
  industry?: string
  keyword?: string
}

export function SearchPage() {
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<SearchFilters>({})

  // Initial load — search with empty filters on mount
  useEffect(() => {
    let mounted = true
    ;(async function load() {
      try {
        const res = await fetch('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filters: {}, limit: 50, offset: 0 }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (mounted) setResults(data.results)
        setLoading(false)
      } catch (e) {
        console.error('Search load error:', e)
        if (mounted) {
          setError((e as Error).message)
          setLoading(false)
        }
      }
    })()
    return () => { mounted = false }
  }, [])

  const handleSearch = async (newFilters: SearchFilters) => {
    setFilters(newFilters)
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters: newFilters, limit: 50, offset: 0 }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResults(data.results)
      setLoading(false)
    } catch (e) {
      console.error('Search error:', e)
      setError((e as Error).message)
      setLoading(false)
    }
  }

  if (loading) {
    return <div>Loading leads...</div>
  }

  if (error) {
    return <div>Error: {error}<br/>Try adjusting search filters.</div>
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">LeadEngine — Search</h1>

      {/* Simple filter form */}
      <div className="mb-4 space-y-3">
        <div>
          <label className="sr-only">Keyword</label>
          <input
            className="input-field"
            type="text"
            placeholder="Keyword (title, company, location)"
            onChange={(e) =>
              handleSearch({
                ...filters,
                keyword: e.target.value.trim(),
              })}
            defaultValue={filters.keyword || ''}
          />
        </div>

        <div>
          <label className="sr-only">Department</label>
          <input
            className="input-field"
            type="text"
            placeholder="Department"
            onChange={(e) =>
              handleSearch({
                ...filters,
                department: e.target.value.trim(),
              })}
            defaultValue={filters.department || ''}
          />
        </div>

        <div>
          <label className="sr-only">Location</label>
          <input
            className="input-field"
            type="text"
            placeholder="Location"
            onChange={(e) =>
              handleSearch({
                ...filters,
                location: e.target.value.trim(),
              })}
            defaultValue={filters.location || ''}
          />
        </div>
      </div>

      {/* Results list */}
      <div className="mt-6 space-y-4">
        {results.length === 0 && (
          <p className="text-muted-foreground">
            No leads found. Try adjusting your search filters.
          </p>
        )}

        {results.map((lead) => (
          <div key={lead.id} className="border rounded p-4 hover:transition-colors">
            <div className="font-medium truncate">{lead.full_name}</div>
            <div className="text-sm text-muted-foreground truncate">
              {lead.current_title} &bull; {lead.current_company}
            </div>
            <div className="text-xs text-muted-foreground">
              {lead.department} {lead.seniority} {lead.location} {lead.industry}
            </div>
          </div>
        ))}

        {results.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Showing {results.length} results{' '}
            {filters.keyword && `for "${filters.keyword}"`}
          </p>
        )}
      </div>
    </div>
  )
}
