import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { LogOut, Search, User as UserIcon, Bookmark, X } from 'lucide-react'
import { api, img } from '../api'
import { useAuth } from '../store.jsx'

export function Logo() {
  return (
    <Link to="/" className="logo" aria-label="CineMind home">
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
        <circle cx="16" cy="16" r="6.5" fill="currentColor" />
        <circle cx="16" cy="16" r="11.5" fill="none" stroke="currentColor" strokeOpacity=".45" strokeWidth="1.6" strokeDasharray="2 3.2" />
      </svg>
      <span>CineMind</span>
    </Link>
  )
}

function SearchBox() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [hits, setHits] = useState([])
  const [cursor, setCursor] = useState(-1)
  const nav = useNavigate()
  const ref = useRef()
  const input = useRef()

  useEffect(() => {
    if (q.trim().length < 2) { setHits([]); return }
    const t = setTimeout(() => api.get(`/search/suggest?q=${encodeURIComponent(q)}`).then(setHits).catch(() => {}), 160)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    const away = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', away)
    return () => document.removeEventListener('mousedown', away)
  }, [])

  const go = (path) => { setOpen(false); setQ(''); setHits([]); nav(path) }
  const submit = (e) => {
    e.preventDefault()
    if (cursor >= 0 && hits[cursor]) return go(`/movie/${hits[cursor].id}`)
    if (q.trim()) go(`/browse?q=${encodeURIComponent(q.trim())}`)
  }
  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setCursor((c) => Math.min(c + 1, hits.length - 1)) }
    if (e.key === 'ArrowUp') { e.preventDefault(); setCursor((c) => Math.max(c - 1, -1)) }
    if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div className={`search ${open ? 'open' : ''}`} ref={ref}>
      <button className="icon-btn" aria-label="Search films" onClick={() => { setOpen(true); setTimeout(() => input.current?.focus(), 50) }}>
        <Search size={19} />
      </button>
      <form onSubmit={submit} role="search">
        <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setCursor(-1) }} onKeyDown={onKey}
          placeholder="Titles, directors, actors, moods" aria-label="Search" />
        {q && <button type="button" className="icon-btn clear" aria-label="Clear" onClick={() => { setQ(''); input.current?.focus() }}><X size={15} /></button>}
      </form>
      <AnimatePresence>
        {open && hits.length > 0 && (
          <motion.ul className="suggest" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
            {hits.map((h, i) => (
              <li key={h.id}>
                <button className={i === cursor ? 'on' : ''} onMouseEnter={() => setCursor(i)} onClick={() => go(`/movie/${h.id}`)}>
                  <img src={img(h.poster)} alt="" />
                  <span><b>{h.title}</b><small>{h.year} &nbsp;{h.genres.join(', ')}</small></span>
                </button>
              </li>
            ))}
            <li><button className="all" onClick={() => go(`/browse?q=${encodeURIComponent(q)}`)}>See all results for “{q}”</button></li>
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const [solid, setSolid] = useState(false)
  const [menu, setMenu] = useState(false)
  const loc = useLocation()

  useEffect(() => {
    const on = () => setSolid(window.scrollY > 24)
    on()
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [])
  useEffect(() => setMenu(false), [loc.pathname])

  return (
    <header className={`nav ${solid ? 'solid' : ''}`}>
      <div className="nav-inner">
        <Logo />
        <nav className="nav-links" aria-label="Primary">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/browse">Browse</NavLink>
          <NavLink to="/for-you">For you</NavLink>
          <NavLink to="/watchlist">Watchlist</NavLink>
          <NavLink to="/about">How it works</NavLink>
        </nav>
        <div className="nav-right">
          <SearchBox />
          {user ? (
            <div className="avatar-wrap">
              <button className="avatar" style={{ background: user.avatar_color }} onClick={() => setMenu((m) => !m)} aria-label="Account menu" aria-expanded={menu}>
                {user.username[0].toUpperCase()}
              </button>
              <AnimatePresence>
                {menu && (
                  <motion.div className="menu" initial={{ opacity: 0, y: -6, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.14 }}>
                    <div className="menu-head"><b>{user.username}</b><small>{user.email}</small></div>
                    <Link to="/profile"><UserIcon size={16} /> Profile</Link>
                    <Link to="/watchlist"><Bookmark size={16} /> Watchlist</Link>
                    <button onClick={logout}><LogOut size={16} /> Sign out</button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <Link className="btn small" to="/login">Sign in</Link>
          )}
        </div>
      </div>
    </header>
  )
}
