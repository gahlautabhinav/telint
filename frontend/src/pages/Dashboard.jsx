import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, Activity, Plus, X, ChevronRight, RefreshCw } from 'lucide-react'
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

/* ─── Stats strip ─────────────────────────────────────────── */
function StatsStrip({ targets }) {
  const totalMembers = targets.reduce((acc, t) => acc + (t.member_count || 0), 0)
  const activeMonitors = targets.filter(t => t.monitoring).length

  const stats = [
    {
      label: 'Total Targets',
      value: targets.length,
      icon: LayoutDashboard,
      accent: true,
    },
    {
      label: 'Total Members',
      value: totalMembers.toLocaleString(),
      icon: Users,
      accent: false,
    },
    {
      label: 'Active Monitors',
      value: activeMonitors,
      icon: Activity,
      accent: activeMonitors > 0,
    },
  ]

  return (
    <div style={stripStyles.wrap}>
      {stats.map((s, i) => {
        const Icon = s.icon
        return (
          <div key={s.label} style={stripStyles.card}>
            <div style={stripStyles.top}>
              <span style={stripStyles.label}>{s.label}</span>
              <span style={{ color: s.accent ? 'var(--color-coral)' : 'var(--color-muted)' }}>
                <Icon size={16} strokeWidth={2} />
              </span>
            </div>
            <span style={stripStyles.value}>{s.value}</span>
          </div>
        )
      })}
    </div>
  )
}

const stripStyles = {
  wrap: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
    marginBottom: '32px',
  },
  card: {
    background: 'var(--color-soft-stone)',
    border: '1px solid var(--color-hairline)',
    borderRadius: 'var(--radius-sm)',
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  top: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  label: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '13px',
    color: 'var(--color-body-muted)',
    fontWeight: 500,
  },
  value: {
    fontFamily: "'Space Grotesk', system-ui",
    fontSize: '28px',
    fontWeight: 600,
    color: 'var(--color-ink)',
    lineHeight: 1,
  },
}

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

/* ─── Target card ─────────────────────────────────────────── */
function TargetCard({ target, onScrape, onToggleMonitor, index }) {
  const navigate = useNavigate()
  const [scraping, setScraping] = useState(false)
  const [scrapeResult, setScrapeResult] = useState(null)

  const handleScrape = async () => {
    setScraping(true)
    setScrapeResult(null)
    try {
      const result = await onScrape(target.handle)
      setScrapeResult(result)
      setTimeout(() => setScrapeResult(null), 3500)
    } catch {
      setScrapeResult({ error: true })
      setTimeout(() => setScrapeResult(null), 3000)
    } finally {
      setScraping(false)
    }
  }

  return (
    <div
      style={{
        ...cardStyles.card,
        animationDelay: `${index * 60}ms`,
        animation: 'cardReveal 0.25s ease-out both',
      }}
    >
      {/* Header */}
      <div style={cardStyles.header}>
        <div style={cardStyles.handleRow}>
          <span style={cardStyles.handle}>@{target.handle}</span>
          <TypeBadge type={target.type} />
        </div>
        {target.display_name && (
          <span style={cardStyles.displayName}>{target.display_name}</span>
        )}
      </div>

      <div style={cardStyles.separator} />

      {/* Stats row */}
      <div style={cardStyles.statsRow}>
        <div>
          <span style={cardStyles.memberCount}>
            {(target.member_count || 0).toLocaleString()}
          </span>
          <span style={cardStyles.memberLabel}> members</span>
        </div>
        <span style={cardStyles.lastScraped}>
          {target.last_scraped ? formatDate(target.last_scraped) : 'Never scraped'}
        </span>
      </div>

      {/* Monitor toggle */}
      <div style={cardStyles.monitorRow}>
        <button
          style={{
            ...cardStyles.monitorBtn,
            ...(target.monitoring ? cardStyles.monitorActive : cardStyles.monitorInactive),
          }}
          onClick={() => onToggleMonitor(target.handle, !target.monitoring)}
        >
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: target.monitoring ? 'var(--color-coral)' : 'var(--color-muted)',
            flexShrink: 0,
            display: 'inline-block',
          }} />
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', letterSpacing: '0.08em' }}>
            {target.monitoring ? 'MONITORING' : 'MONITOR OFF'}
          </span>
        </button>
      </div>

      {/* Scrape result flash */}
      {scrapeResult && (
        <div style={{
          ...cardStyles.flashResult,
          ...(scrapeResult.error ? cardStyles.flashError : cardStyles.flashSuccess),
          animation: 'flashGreen 3.5s ease forwards',
        }}>
          {scrapeResult.error
            ? 'Scrape failed. Check connection.'
            : `Collected ${scrapeResult.total || 0} members / ${scrapeResult.new || 0} new`
          }
        </div>
      )}

      <div style={cardStyles.separator} />

      {/* Actions */}
      <div style={cardStyles.actions}>
        <button
          className="btn-outline"
          onClick={handleScrape}
          disabled={scraping}
          style={{ fontSize: '13px', padding: '6px 14px' }}
        >
          {scraping ? (
            <>
              <span className="spinner spinner-dark" />
              Scraping…
            </>
          ) : (
            <>
              <RefreshCw size={13} strokeWidth={2} />
              Scrape
            </>
          )}
        </button>
        <button
          className="btn-secondary"
          onClick={() => navigate(`/target/${target.handle}`)}
          style={{ fontSize: '13px', marginLeft: 'auto' }}
        >
          Members
          <ChevronRight size={14} strokeWidth={2} />
        </button>
      </div>
    </div>
  )
}

const cardStyles = {
  card: {
    background: 'var(--color-soft-stone)',
    border: '1px solid var(--color-hairline)',
    borderRadius: 'var(--radius-sm)',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  handleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  handle: {
    fontFamily: "'Space Grotesk', system-ui",
    fontSize: '17px',
    fontWeight: 600,
    color: 'var(--color-ink)',
    letterSpacing: '-0.2px',
  },
  displayName: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '13px',
    color: 'var(--color-body-muted)',
  },
  separator: {
    height: '1px',
    background: 'var(--color-hairline)',
    margin: '0 -0px',
  },
  statsRow: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: '8px',
  },
  memberCount: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '16px',
    fontWeight: 500,
    color: 'var(--color-ink)',
  },
  memberLabel: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '13px',
    color: 'var(--color-muted)',
  },
  lastScraped: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '11px',
    color: 'var(--color-muted)',
    textAlign: 'right',
  },
  monitorRow: {
    display: 'flex',
    alignItems: 'center',
  },
  monitorBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    background: 'transparent',
    border: '1px solid var(--color-hairline)',
    borderRadius: 'var(--radius-pill)',
    padding: '4px 10px',
    cursor: 'pointer',
    transition: 'border-color 0.15s ease, background 0.15s ease',
  },
  monitorActive: {
    borderColor: 'rgba(255, 119, 89, 0.4)',
    background: 'rgba(255, 119, 89, 0.05)',
  },
  monitorInactive: {
    borderColor: 'var(--color-hairline)',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  flashResult: {
    padding: '8px 12px',
    borderRadius: 'var(--radius-xs)',
    fontSize: '12px',
    fontFamily: "'DM Sans', system-ui",
    fontWeight: 500,
  },
  flashSuccess: {
    background: 'var(--color-pale-green)',
    color: 'var(--color-deep-green)',
    border: '1px solid rgba(0, 60, 51, 0.15)',
  },
  flashError: {
    background: '#fff0f0',
    color: 'var(--color-error)',
    border: '1px solid rgba(179, 0, 0, 0.15)',
  },
}

/* ─── Add target panel ────────────────────────────────────── */
function AddTargetPanel({ onAdd, onClose }) {
  const [handle, setHandle] = useState('')
  const [type, setType] = useState('group')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!handle.trim()) { setError('Handle is required'); return }
    setError('')
    setLoading(true)
    try {
      await onAdd({ handle: handle.replace(/^@/, ''), type })
      setHandle('')
      setType('group')
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to add target')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={panelStyles.wrap}>
      <div style={panelStyles.inner}>
        <div style={panelStyles.titleRow}>
          <span style={panelStyles.title}>Add Target</span>
          <button style={panelStyles.closeBtn} onClick={onClose} aria-label="Close">
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        <form onSubmit={handleSubmit} style={panelStyles.form}>
          <div style={panelStyles.fieldRow}>
            <div style={panelStyles.field}>
              <label style={panelStyles.label}>Handle</label>
              <input
                style={panelStyles.input}
                type="text"
                placeholder="@grouphandle"
                value={handle}
                onChange={e => setHandle(e.target.value)}
                autoFocus
              />
            </div>
            <div style={panelStyles.field}>
              <label style={panelStyles.label}>Type</label>
              <select
                style={panelStyles.select}
                value={type}
                onChange={e => setType(e.target.value)}
              >
                <option value="group">Group</option>
                <option value="channel">Channel</option>
              </select>
            </div>
          </div>
          {error && (
            <span style={panelStyles.error}>{error}</span>
          )}
          <div style={panelStyles.formActions}>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? <><span className="spinner" />Adding…</> : 'Add Target'}
            </button>
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const panelStyles = {
  wrap: {
    borderBottom: '1px solid var(--color-hairline)',
    background: 'var(--color-canvas)',
    overflow: 'hidden',
  },
  inner: {
    padding: '20px 32px 24px',
    maxWidth: '600px',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
  },
  title: {
    fontFamily: "'Space Grotesk', system-ui",
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--color-ink)',
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--color-muted)',
    padding: '4px',
    borderRadius: 'var(--radius-xs)',
    display: 'flex',
    alignItems: 'center',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  fieldRow: {
    display: 'flex',
    gap: '12px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    flex: 1,
  },
  label: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--color-body-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  input: {
    padding: '10px 12px',
    border: '1px solid var(--color-hairline)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '14px',
    fontFamily: "'DM Sans', system-ui",
    color: 'var(--color-ink)',
    background: 'var(--color-canvas)',
    outline: 'none',
    transition: 'border-color 0.15s ease',
  },
  select: {
    padding: '10px 12px',
    border: '1px solid var(--color-hairline)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '14px',
    fontFamily: "'DM Sans', system-ui",
    color: 'var(--color-ink)',
    background: 'var(--color-canvas)',
    outline: 'none',
    cursor: 'pointer',
  },
  error: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '13px',
    color: 'var(--color-error)',
  },
  formActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    paddingTop: '4px',
  },
}

/* ─── Dashboard page ─────────────────────────────────────── */
export default function Dashboard() {
  const [targets, setTargets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAddPanel, setShowAddPanel] = useState(false)

  const loadTargets = useCallback(async () => {
    try {
      const data = await api.getTargets()
      setTargets(Array.isArray(data) ? data : [])
    } catch (err) {
      setError('Failed to load targets.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTargets()
  }, [loadTargets])

  const handleAddTarget = async (body) => {
    const added = await api.addTarget(body)
    if (added && added.id) setTargets(prev => [...prev, added])
  }

  const handleScrape = async (handle) => {
    const result = await api.scrape({ handle })
    // Refresh targets to update member count / last scraped
    loadTargets()
    return result
  }

  const handleToggleMonitor = async (handle, enabled) => {
    try {
      await api.setMonitor({ handle, enabled })
      setTargets(prev => prev.map(t =>
        t.handle === handle ? { ...t, monitoring: enabled } : t
      ))
    } catch {
      // silent — user still sees previous state
    }
  }

  const topBarActions = (
    <button
      className="btn-primary"
      onClick={() => setShowAddPanel(p => !p)}
    >
      <Plus size={15} strokeWidth={2.5} />
      Add Target
    </button>
  )

  return (
    <Layout title="Targets" actions={topBarActions}>
      {/* Slide-down add panel */}
      {showAddPanel && (
        <div style={{ margin: '-32px -32px 32px', overflow: 'hidden' }}>
          <AddTargetPanel
            onAdd={handleAddTarget}
            onClose={() => setShowAddPanel(false)}
          />
        </div>
      )}

      {error && (
        <div style={{ color: 'var(--color-error)', fontFamily: "'DM Sans', system-ui", fontSize: '14px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {loading ? (
        <>
          {/* Skeleton stats strip */}
          <div style={{ ...stripStyles.wrap }}>
            {[0, 1, 2].map(i => (
              <div key={i} className="card" style={{ height: '88px' }}>
                <div className="skeleton" style={{ height: '13px', width: '60%' }} />
                <div className="skeleton" style={{ height: '28px', width: '40%', marginTop: '8px' }} />
              </div>
            ))}
          </div>
          {/* Skeleton cards */}
          <div style={gridStyles.grid}>
            {[0, 1, 2, 3, 4, 5].map(i => (
              <div key={i} className="card" style={{ minHeight: '200px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="skeleton" style={{ height: '20px', width: '55%' }} />
                <div className="skeleton" style={{ height: '1px', width: '100%' }} />
                <div className="skeleton" style={{ height: '16px', width: '35%' }} />
                <div className="skeleton" style={{ height: '24px', width: '45%' }} />
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <StatsStrip targets={targets} />

          {targets.length === 0 ? (
            <div style={emptyStyles.wrap}>
              <LayoutDashboard size={32} strokeWidth={1.5} style={{ color: 'var(--color-muted)' }} />
              <span style={emptyStyles.text}>No targets yet. Add a Telegram group or channel to get started.</span>
            </div>
          ) : (
            <div style={gridStyles.grid}>
              {targets.map((target, i) => (
                <TargetCard
                  key={target.handle}
                  target={target}
                  index={i}
                  onScrape={handleScrape}
                  onToggleMonitor={handleToggleMonitor}
                />
              ))}
            </div>
          )}
        </>
      )}
    </Layout>
  )
}

const gridStyles = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '16px',
  },
}

const emptyStyles = {
  wrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    padding: '80px 32px',
    color: 'var(--color-muted)',
  },
  text: {
    fontFamily: "'DM Sans', system-ui",
    fontSize: '15px',
    color: 'var(--color-body-muted)',
    textAlign: 'center',
    maxWidth: '360px',
  },
}
