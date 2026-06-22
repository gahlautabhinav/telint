import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Search, ChevronUp, ChevronDown,
  MessageSquare, RefreshCw
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

/* ─── MediaBadge ──────────────────────────────────────────── */
function MediaBadge({ type }) {
  if (!type) return <span style={{ color: 'var(--color-muted)' }}>—</span>
  const colors = {
    photo: { bg: 'var(--color-pale-blue)', color: 'var(--color-action-blue)' },
    document: { bg: 'var(--color-soft-stone)', color: 'var(--color-muted)' },
  }
  const c = colors[type] || { bg: 'var(--color-soft-stone)', color: 'var(--color-muted)' }
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
      {type}
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

/* ─── Skeleton rows ─────────────────────────────────────── */
function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, i) => (
        <tr key={i} style={{ borderBottom: '1px solid var(--color-hairline)' }}>
          {Array.from({ length: 9 }).map((__, j) => (
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

/* ─── Messages page ──────────────────────────────────────── */
export default function Messages() {
  const { handle } = useParams()
  const [messages, setMessages] = useState([])
  const [totalCount, setTotalCount] = useState(null)
  const [lastScraped, setLastScraped] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [sortCol, setSortCol] = useState('date')
  const [sortDir, setSortDir] = useState('desc')
  const [page, setPage] = useState(0)
  const [scraping, setScraping] = useState(false)
  const [scrapeResult, setScrapeResult] = useState(null)
  const [scrapeLimit, setScrapeLimit] = useState(200)

  const loadMessages = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getMessages(handle)
      setMessages(Array.isArray(data.messages) ? data.messages : [])
      if (data.count != null) setTotalCount(data.count)
      if (data.last_scraped) setLastScraped(data.last_scraped)
    } catch {
      setError('Failed to load messages.')
    } finally {
      setLoading(false)
    }
  }, [handle])

  useEffect(() => {
    loadMessages()
  }, [loadMessages])

  const handleScrape = async () => {
    setScraping(true)
    setScrapeResult(null)
    try {
      const result = await api.scrapeMessages(handle, scrapeLimit)
      setScrapeResult(result)
      loadMessages()
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
    return messages.filter(m =>
      !q ||
      (m.sender_username || '').toLowerCase().includes(q) ||
      (m.sender_first_name || '').toLowerCase().includes(q) ||
      (m.sender_last_name || '').toLowerCase().includes(q) ||
      (m.text || '').toLowerCase().includes(q)
    )
  }, [messages, filter])

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
    { key: 'message_id', label: 'MSG ID', mono: true, align: 'right' },
    { key: 'sender_username', label: 'SENDER', mono: true },
    { key: 'sender_first_name', label: 'FIRST NAME' },
    { key: 'sender_last_name', label: 'LAST NAME' },
    { key: 'sender_user_id', label: 'USER ID', mono: true, align: 'right' },
    { key: 'media_type', label: 'MEDIA' },
    { key: 'reply_to_message_id', label: 'REPLY TO', mono: true, align: 'right' },
    { key: 'date', label: 'DATE' },
    { key: 'text', label: 'TEXT' },
  ]

  /* ─── actions ───────────────────────────────────────────── */
  const topBarActions = (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      {scrapeResult && !scrapeResult.error && (
        <span style={{
          fontFamily: "'DM Sans', system-ui",
          fontSize: '13px',
          color: 'var(--color-deep-green)',
          fontWeight: 500,
          background: 'var(--color-pale-green)',
          padding: '5px 12px',
          borderRadius: 'var(--radius-pill)',
          animation: 'flashGreen 4s ease forwards',
        }}>
          {scrapeResult.messages_saved || 0} saved / {scrapeResult.new_senders || 0} new senders
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
      <input
        type="number"
        min={1}
        max={5000}
        value={scrapeLimit}
        onChange={e => setScrapeLimit(Math.max(1, parseInt(e.target.value) || 200))}
        style={{
          width: '70px',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '12px',
          padding: '6px 8px',
          border: '1px solid var(--color-hairline)',
          borderRadius: 'var(--radius-sm)',
          outline: 'none',
          textAlign: 'center',
        }}
        aria-label="Message limit"
      />
      <span style={{ fontSize: '12px', color: 'var(--color-muted)', fontFamily: "'DM Sans', system-ui" }}>
        msgs max
      </span>
      <button
        className="btn-primary"
        onClick={handleScrape}
        disabled={scraping}
        style={{ minWidth: '140px' }}
      >
        {scraping ? (
          <>
            <span className="spinner" />
            Scraping…
          </>
        ) : (
          <>
            <RefreshCw size={14} strokeWidth={2} />
            Scrape Messages
          </>
        )}
      </button>
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
              @{handle} Messages
            </span>
          </span>
        </span>
      }
      actions={topBarActions}
    >
      {/* Stats */}
      <div style={pageStyles.statsRow}>
        <span style={pageStyles.statItem}>
          <span style={pageStyles.statValue}>
            {(totalCount ?? messages.length).toLocaleString()}
          </span>
          <span style={pageStyles.statLabel}>messages</span>
        </span>
        {lastScraped && (
          <>
            <span style={pageStyles.statDivider} />
            <span style={pageStyles.statItem}>
              <span style={pageStyles.statLabel}>Last scraped:</span>
              <span style={{ fontFamily: "'DM Sans', system-ui", fontSize: '13px', color: 'var(--color-ink)' }}>
                {formatDate(lastScraped)}
              </span>
            </span>
          </>
        )}
      </div>

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
            placeholder="Filter by sender or message text…"
            value={filter}
            onChange={e => { setFilter(e.target.value); setPage(0) }}
            style={pageStyles.searchInput}
            aria-label="Filter messages"
          />
        </div>
        <span style={pageStyles.countLabel}>
          {sorted.length.toLocaleString()} of {messages.length.toLocaleString()}
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
                    <MessageSquare size={28} strokeWidth={1.5} style={{ color: 'var(--color-muted)' }} />
                    <span>
                      {messages.length === 0
                        ? 'No messages scraped yet. Use Scrape Messages to collect evidence.'
                        : 'No messages match your filter.'}
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              pageRows.map((m, i) => (
                <tr key={`${m.message_id}-${i}`} style={pageStyles.tr}>
                  <td style={{ ...pageStyles.td, textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--color-slate)' }}>
                    {m.message_id ?? '—'}
                  </td>
                  <td style={{ ...pageStyles.td, fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
                    {m.sender_username ? `@${m.sender_username}` : <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={pageStyles.td}>
                    {m.sender_first_name || <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={pageStyles.td}>
                    {m.sender_last_name || <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={{ ...pageStyles.td, textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--color-slate)' }}>
                    {m.sender_user_id ?? '—'}
                  </td>
                  <td style={pageStyles.td}>
                    <MediaBadge type={m.media_type} />
                  </td>
                  <td style={{ ...pageStyles.td, textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--color-slate)' }}>
                    {m.reply_to_message_id ?? <span style={{ color: 'var(--color-muted)' }}>—</span>}
                  </td>
                  <td style={{ ...pageStyles.td, fontSize: '12px', color: 'var(--color-slate)', whiteSpace: 'nowrap' }}>
                    {formatDate(m.date)}
                  </td>
                  <td style={{ ...pageStyles.td, maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {m.text || <span style={{ color: 'var(--color-muted)' }}>—</span>}
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
