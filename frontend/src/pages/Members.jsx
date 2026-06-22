import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Search, ChevronUp, ChevronDown,
  Check, Target, RefreshCw, Download
} from 'lucide-react'
import Layout from '../components/Layout'
import { api } from '../api'

/* ─── helpers ─────────────────────────────────────────────── */
function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const PAGE_SIZE = 50

/* ─── Type badge ──────────────────────────────────────────── */
function TypeBadge({ type }) {
  const isGroup = type === 'group'
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '10px',
      fontWeight: 500,
      padding: '3px 8px',
      borderRadius: 'var(--radius-pill)',
      letterSpacing: '0.08em',
      ...(isGroup
        ? { background: 'var(--color-deep-green)', color: 'var(--color-on-dark)' }
        : { border: '1px solid var(--color-coral)', color: 'var(--color-coral)', background: 'transparent' }
      ),
    }}>
      {type ? type.toUpperCase() : 'GROUP'}
    </span>
  )
}

/* ─── VIA chip ────────────────────────────────────────────── */
function ViaChip({ via }) {
  const config = {
    group_members: { bg: 'var(--color-deep-green)', color: 'var(--color-on-dark)', label: 'group' },
    reaction: { bg: 'var(--color-coral-soft)', color: '#7a3520', label: 'reaction' },
    comment: { bg: 'var(--color-pale-blue)', color: 'var(--color-action-blue)', label: 'comment' },
  }
  const c = config[via] || { bg: 'var(--color-soft-stone)', color: 'var(--color-muted)', label: via || '—' }
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '10px',
      fontWeight: 500,
      padding: '3px 7px',
      borderRadius: 'var(--radius-pill)',
      background: c.bg,
      color: c.color,
      letterSpacing: '0.05em',
      whiteSpace: 'nowrap',
    }}>
      {c.label}
    </span>
  )
}

/* ─── Sort indicator ─────────────────────────────────────── */
function SortIndicator({ active, dir }) {
  if (!active) return <ChevronDown size={12} strokeWidth={2} style={{ opacity: 0.3 }} />
  return dir === 'asc'
    ? <ChevronUp size={12} strokeWidth={2} style={{ color: 'var(--color-coral)' }} />
    : <ChevronDown size={12} strokeWidth={2} style={{ color: 'var(--color-coral)' }} />
}

/* ─── Admin badge ────────────────────────────────────────── */
function AdminBadge() {
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '10px',
      fontWeight: 500,
      padding: '3px 8px',
      borderRadius: 'var(--radius-pill)',
      background: 'var(--color-coral)',
      color: '#fff',
      letterSpacing: '0.08em',
    }}>
      ADMIN
    </span>
  )
}

/* ─── Skeleton rows ─────────────────────────────────────── */
function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, i) => (
        <tr key={i} style={{ borderBottom: '1px solid var(--color-hairline)' }}>
          {Array.from({ length: 11 }).map((__, j) => (
            <td key={j} style={{ padding: '12px 14px' }}>
              <div
                className="skeleton"
                style={{ height: '12px', width: j === 0 ? '80px' : j === 1 ? '100px' : '70px' }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

/* ─── Members page ───────────────────────────────────────── */
export default function Members() {
  const { handle } = useParams()
  const [target, setTarget] = useState(null)
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [sortCol, setSortCol] = useState('user_id')
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(0)
  const [scraping, setScraping] = useState(false)
  const [scrapeResult, setScrapeResult] = useState(null)

  const loadMembers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getMembers(handle)
      // data can be { target, members } or just array
      if (Array.isArray(data)) {
        setMembers(data)
      } else {
        setMembers(Array.isArray(data.members) ? data.members : [])
        if (data.target) setTarget(data.target)
      }
    } catch {
      setError('Failed to load members.')
    } finally {
      setLoading(false)
    }
  }, [handle])

  useEffect(() => {
    loadMembers()
  }, [loadMembers])

  const handleScrape = async () => {
    setScraping(true)
    setScrapeResult(null)
    try {
      const result = await api.scrape({ handle })
      setScrapeResult(result)
      loadMembers()
      setTimeout(() => setScrapeResult(null), 4000)
    } catch {
      setScrapeResult({ error: true })
      setTimeout(() => setScrapeResult(null), 3000)
    } finally {
      setScraping(false)
    }
  }

  /* ─── filter + sort ─────────────────────────────────────── */
  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase()
    return members.filter(m =>
      !q ||
      (m.username || '').toLowerCase().includes(q) ||
      (m.first_name || '').toLowerCase().includes(q) ||
      (m.last_name || '').toLowerCase().includes(q)
    )
  }, [members, filter])

  const sorted = useMemo(() => {
    const col = sortCol
    return [...filtered].sort((a, b) => {
      const av = a[col] ?? ''
      const bv = b[col] ?? ''
      const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv))
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortCol, sortDir])

  const pageRows = useMemo(() => {
    const start = page * PAGE_SIZE
    return sorted.slice(start, start + PAGE_SIZE)
  }, [sorted, page])

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(col)
      setSortDir('asc')
    }
    setPage(0)
  }

  /* ─── columns ───────────────────────────────────────────── */
  const columns = [
    { key: 'user_id', label: 'USER ID', mono: true, align: 'right' },
    { key: 'username', label: 'USERNAME' },
    { key: 'first_name', label: 'FIRST NAME' },
    { key: 'last_name', label: 'LAST NAME' },
    { key: 'phone', label: 'PHONE', mono: true },
    { key: 'is_bot', label: 'BOT' },
    { key: 'scraped_via', label: 'VIA' },
    { key: 'first_seen', label: 'FIRST SEEN' },
    { key: 'last_seen', label: 'LAST SEEN' },
    { key: 'is_admin', label: 'ADMIN' },
    { key: 'admin_title', label: 'ADMIN TITLE' },
  ]

  /* ─── actions ───────────────────────────────────────────── */
  const topBarActions = (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      {scrapeResult && !scrapeResult.error && (
        <span style={{
          fontFamily: "'DM Sans', system-ui",
          fontSize: '13px',
          color: 'var(--color-success-fg)',
          fontWeight: 500,
          background: 'var(--color-pale-green)',
          padding: '5px 12px',
          borderRadius: 'var(--radius-pill)',
          animation: 'flashGreen 4s ease forwards',
        }}>
          {scrapeResult.total || 0} members / {scrapeResult.new || 0} new
        </span>
      )}
      {scrapeResult && scrapeResult.error && (
        <span style={{
          fontFamily: "'DM Sans', system-ui",
          fontSize: '13px',
          color: 'var(--color-error)',
          fontWeight: 500,
        }}>
          Scrape failed
        </span>
      )}
      <button
        className="btn-primary"
        onClick={handleScrape}
        disabled={scraping}
        style={{ minWidth: '120px' }}
      >
        {scraping ? (
          <>
            <span className="spinner" />
            Scraping…
          </>
        ) : (
          <>
            <RefreshCw size={14} strokeWidth={2} />
            Scrape Now
          </>
        )}
      </button>
      <a
        href={api.exportData(handle, 'csv')}
        download
        className="btn-outline"
        aria-label="Export as CSV"
      >
        <Download size={13} strokeWidth={2} />
        Export CSV
      </a>
      <a
        href={api.exportData(handle, 'json')}
        download
        className="btn-outline"
        aria-label="Export as JSON"
      >
        <Download size={13} strokeWidth={2} />
        Export JSON
      </a>
    </div>
  )

  return (
    <Layout
      title={
        <span style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <Link
            to="/"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              color: 'var(--color-action-blue)',
              fontFamily: "'DM Sans', system-ui",
              fontSize: '13px',
              fontWeight: 400,
              textDecoration: 'none',
              marginBottom: '2px',
            }}
          >
            <ArrowLeft size={13} strokeWidth={2} />
            Targets
          </Link>
          <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{
              fontFamily: "'Space Grotesk', system-ui",
              fontSize: '24px',
              fontWeight: 600,
              letterSpacing: '-0.3px',
            }}>
              @{handle}
            </span>
            {target && <TypeBadge type={target.type} />}
          </span>
        </span>
      }
      actions={topBarActions}
    >
      {/* Stats */}
      {target && (
        <div style={pageStyles.statsRow}>
          <span style={pageStyles.statItem}>
            <span style={pageStyles.statValue}>{(target.member_count || members.length).toLocaleString()}</span>
            <span style={pageStyles.statLabel}>members</span>
          </span>
          <span style={pageStyles.statDivider} />
          <span style={pageStyles.statItem}>
            <span style={pageStyles.statLabel}>Last scraped:</span>
            <span style={{ fontFamily: "'DM Sans', system-ui", fontSize: '13px', color: 'var(--color-ink)' }}>
              {formatDate(target.last_scraped)}
            </span>
          </span>
        </div>
      )}

      {error && (
        <div style={{ color: 'var(--color-error)', fontFamily: "'DM Sans', system-ui", fontSize: '14px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {/* Search/filter */}
      <div style={pageStyles.filterBar}>
        <div style={pageStyles.searchWrap}>
          <Search size={15} strokeWidth={2} style={{ color: 'var(--color-muted)', flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Filter by username or name…"
            value={filter}
            onChange={e => { setFilter(e.target.value); setPage(0) }}
            style={pageStyles.searchInput}
            aria-label="Filter members"
          />
        </div>
        <span style={pageStyles.countLabel}>
          {sorted.length.toLocaleString()} of {members.length.toLocaleString()}
        </span>
      </div>

      {/* Table */}
      <div style={pageStyles.tableWrap}>
        <table style={pageStyles.table}>
          <thead>
            <tr>
              {columns.map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => e.key === 'Enter' && handleSort(col.key)}
                  style={{
                    ...pageStyles.th,
                    textAlign: col.align || 'left',
                    userSelect: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <span style={pageStyles.thInner}>
                    {col.label}
                    <SortIndicator active={sortCol === col.key} dir={sortDir} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <SkeletonRows />
            ) : pageRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={pageStyles.emptyCell}>
                  <div style={pageStyles.emptyState}>
                    <Target size={28} strokeWidth={1.5} style={{ color: 'var(--color-muted)' }} />
                    <span>
                      {members.length === 0
                        ? 'No members scraped yet. Run a scrape to collect data.'
                        : 'No members match your filter.'}
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              pageRows.map((m, i) => (
                <tr key={`${m.target_id}-${m.user_id}-${i}`} style={pageStyles.tr}>
                  <td style={{ ...pageStyles.td, textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--color-slate)' }}>
                    {m.user_id || '—'}
                  </td>
                  <td style={{ ...pageStyles.td, fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
                    {m.username ? `@${m.username}` : <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={pageStyles.td}>
                    {m.first_name || <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={pageStyles.td}>
                    {m.last_name || <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={{ ...pageStyles.td, fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
                    {m.phone || <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={{ ...pageStyles.td, textAlign: 'center' }}>
                    {m.is_bot ? (
                      <Check size={14} strokeWidth={2.5} style={{ color: 'var(--color-coral)' }} />
                    ) : null}
                  </td>
                  <td style={pageStyles.td}>
                    {m.scraped_via ? <ViaChip via={m.scraped_via} /> : <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={{ ...pageStyles.td, fontSize: '12px', color: 'var(--color-slate)', whiteSpace: 'nowrap' }}>
                    {formatDate(m.first_seen)}
                  </td>
                  <td style={{ ...pageStyles.td, fontSize: '12px', color: 'var(--color-slate)', whiteSpace: 'nowrap' }}>
                    {formatDate(m.last_seen)}
                  </td>
                  <td style={{ ...pageStyles.td, textAlign: 'center' }}>
                    {m.is_admin ? <AdminBadge /> : null}
                  </td>
                  <td style={{ ...pageStyles.td, fontSize: '12px', color: 'var(--color-slate)' }}>
                    {m.admin_title || <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={pageStyles.pagination}>
          <button
            className="btn-outline"
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            style={{ fontSize: '13px' }}
          >
            Previous
          </button>
          <span style={pageStyles.pageInfo}>
            Page {page + 1} of {totalPages} &nbsp;·&nbsp; {sorted.length} results
          </span>
          <button
            className="btn-outline"
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            style={{ fontSize: '13px' }}
          >
            Next
          </button>
        </div>
      )}
    </Layout>
  )
}

const pageStyles = {
  statsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '24px',
    paddingBottom: '16px',
    borderBottom: '1px solid var(--color-hairline)',
  },
  statItem: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '6px',
  },
  statValue: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '15px',
    fontWeight: 500,
    color: 'var(--color-ink)',
  },
  statLabel: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '13px',
    color: 'var(--color-muted)',
  },
  statDivider: {
    width: '1px',
    height: '16px',
    background: 'var(--color-hairline)',
  },
  filterBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '16px',
  },
  searchWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flex: 1,
    maxWidth: '380px',
    border: '1px solid var(--color-hairline)',
    borderRadius: 'var(--radius-sm)',
    padding: '8px 12px',
    background: 'var(--color-canvas)',
    transition: 'border-color 0.15s ease',
  },
  searchInput: {
    flex: 1,
    border: 'none',
    outline: 'none',
    fontSize: '13px',
    fontFamily: "'DM Sans', system-ui",
    color: 'var(--color-ink)',
    background: 'transparent',
  },
  countLabel: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--color-muted)',
    marginLeft: 'auto',
  },
  tableWrap: {
    border: '1px solid var(--color-hairline)',
    borderRadius: 'var(--radius-sm)',
    overflow: 'hidden',
    overflowX: 'auto',
    background: 'var(--color-canvas)',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
    fontFamily: "'DM Sans', system-ui",
  },
  th: {
    background: 'var(--color-deep-green)',
    color: 'var(--color-on-dark)',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '10px',
    fontWeight: 500,
    letterSpacing: '0.1em',
    padding: '11px 14px',
    whiteSpace: 'nowrap',
    position: 'sticky',
    top: 0,
  },
  thInner: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
  },
  tr: {
    borderBottom: '1px solid var(--color-hairline)',
    transition: 'background 0.1s ease',
  },
  td: {
    padding: '11px 14px',
    color: 'var(--color-ink)',
    verticalAlign: 'middle',
    whiteSpace: 'nowrap',
    fontFamily: "'DM Sans', system-ui",
    fontSize: '13px',
  },
  emptyCell: {
    padding: '0',
    border: 'none',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '80px 32px',
    color: 'var(--color-body-muted)',
    fontFamily: "'DM Sans', system-ui",
    fontSize: '14px',
    textAlign: 'center',
  },
  pagination: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    marginTop: '20px',
    paddingTop: '16px',
    borderTop: '1px solid var(--color-hairline)',
  },
  pageInfo: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '13px',
    color: 'var(--color-muted)',
  },
}
