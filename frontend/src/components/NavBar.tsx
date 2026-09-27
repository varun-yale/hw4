import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const links = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export function Shield({ size = 34 }: { size?: number }) {
  return (
    <svg className="shield" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M32 3 8 11v19c0 15.5 10.2 26.3 24 31 13.8-4.7 24-15.5 24-31V11L32 3z" fill="currentColor" />
      <path d="M32 8.5 13 15v15c0 12.6 8 21.6 19 25.8 11-4.2 19-13.2 19-25.8V15L32 8.5z" fill="none" stroke="var(--paper)" strokeWidth="2" />
      <text x="32" y="41" textAnchor="middle" fontFamily="Fraunces, Georgia, serif" fontSize="22" fontWeight="700" fill="var(--paper)">
        CC
      </text>
    </svg>
  )
}

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  return (
    <div className={`site-header${scrolled ? ' scrolled' : ''}`}>
      <div className="announce">
        <span>Officially licensed Yale apparel</span>
        <span className="announce-dot hide-xs" aria-hidden="true">✦</span>
        <span className="hide-xs">Visit us at 57 Broadway, New Haven</span>
        <span className="announce-dot hide-sm" aria-hidden="true">✦</span>
        <span className="hide-sm">Live size availability on every item</span>
      </div>
      <header className={`nav${menuOpen ? ' nav-open' : ''}`}>
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <Shield />
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-sub">Yale apparel · New Haven</span>
          </span>
        </Link>
        <button
          className="menu-toggle"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span />
          <span />
          <span />
        </button>
        <div className="nav-menu">
          <nav className="nav-links">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.to === '/'}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="nav-auth">
            {loading ? null : user ? (
              <>
                <span className="nav-greeting">Hi, {user.first_name}</span>
                <button className="btn btn-outline btn-sm" onClick={handleLogout}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="nav-login">
                  Log in
                </NavLink>
                <NavLink to="/signup" className="btn btn-primary btn-sm">
                  Create account
                </NavLink>
              </>
            )}
          </div>
        </div>
      </header>
    </div>
  )
}
