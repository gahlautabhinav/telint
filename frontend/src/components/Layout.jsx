import { NavLink } from 'react-router-dom'
import { LayoutDashboard } from 'lucide-react'

const styles = {
  root: {
    display: 'flex',
    minHeight: '100vh',
    height: '100%',
  },
  sidebar: {
    width: '240px',
    minWidth: '240px',
    background: 'var(--color-deep-green)',
    display: 'flex',
    flexDirection: 'column',
    padding: '0',
    position: 'sticky',
    top: 0,
    height: '100vh',
    overflowY: 'auto',
  },
  logoArea: {
    padding: '28px 24px 24px',
  },
  logoText: {
    fontFamily: "'Space Grotesk', system-ui",
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--color-on-dark)',
    letterSpacing: '-0.3px',
    display: 'block',
    lineHeight: 1,
  },
  logoSub: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '10px',
    color: 'var(--color-coral)',
    letterSpacing: '0.12em',
    marginTop: '4px',
    display: 'block',
  },
  divider: {
    height: '1px',
    background: 'rgba(255,255,255,0.15)',
    margin: '0 16px',
  },
  nav: {
    padding: '16px 12px',
    flex: 1,
  },
  navLinkBase: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '9px 12px',
    borderRadius: 'var(--radius-sm)',
    fontFamily: "'DM Sans', system-ui",
    fontSize: '14px',
    fontWeight: 500,
    color: 'rgba(255,255,255,0.65)',
    textDecoration: 'none',
    transition: 'color 0.15s ease, background 0.15s ease',
    borderLeft: '2px solid transparent',
    marginBottom: '2px',
  },
  bottomArea: {
    padding: '16px 24px 24px',
    borderTop: '1px solid rgba(255,255,255,0.1)',
  },
  versionTag: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    color: 'rgba(255,255,255,0.35)',
    letterSpacing: '0.05em',
  },
  mainArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--color-canvas)',
    minHeight: '100vh',
  },
  topBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 32px',
    borderBottom: '1px solid var(--color-hairline)',
    background: 'var(--color-canvas)',
    position: 'sticky',
    top: 0,
    zIndex: 10,
    minHeight: '64px',
  },
  pageTitle: {
    fontFamily: "'Space Grotesk', system-ui",
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--color-ink)',
    letterSpacing: '-0.2px',
  },
  topBarActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  content: {
    flex: 1,
    padding: '32px',
  },
}

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      style={({ isActive }) => ({
        ...styles.navLinkBase,
        ...(isActive ? {
          color: 'var(--color-on-dark)',
          background: 'rgba(237, 252, 233, 0.1)',
          borderLeft: '2px solid var(--color-coral)',
        } : {}),
      })}
    >
      <Icon size={16} strokeWidth={2} />
      {label}
    </NavLink>
  )
}

export default function Layout({ title, actions, children }) {
  return (
    <div style={styles.root}>
      <aside style={styles.sidebar}>
        <div style={styles.logoArea}>
          <span style={styles.logoText}>telint</span>
          <span style={styles.logoSub}>OSINT</span>
        </div>
        <div style={styles.divider} />
        <nav style={styles.nav}>
          <NavItem to="/" icon={LayoutDashboard} label="Targets" />
        </nav>
        <div style={styles.bottomArea}>
          <span style={styles.versionTag}>v1.0</span>
        </div>
      </aside>

      <div style={styles.mainArea}>
        <header style={styles.topBar}>
          <span style={styles.pageTitle}>{title}</span>
          <div style={styles.topBarActions}>{actions}</div>
        </header>
        <main style={styles.content}>
          {children}
        </main>
      </div>
    </div>
  )
}
