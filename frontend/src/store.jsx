import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, X } from 'lucide-react'
import { api, getToken, setToken } from './api'

/* ---------------------------------------------------------------- toasts */
const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((message, kind = 'ok') => {
    const id = Math.random().toString(36).slice(2)
    setItems((x) => [...x, { id, message, kind }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 3200)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div key={t.id} className={`toast ${t.kind}`} initial={{ opacity: 0, y: 16, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 8 }} transition={{ duration: 0.2 }}>
              {t.kind === 'ok' ? <Check size={16} /> : <X size={16} />}
              {t.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  )
}

/* ------------------------------------------------------------------ auth */
const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api.get('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const onOut = () => { setToken(null); setUser(null) }
    window.addEventListener('cinemind:logout', onOut)
    return () => window.removeEventListener('cinemind:logout', onOut)
  }, [])

  const authenticate = async (path, body) => {
    const r = await api.post(path, body)
    setToken(r.token)
    setUser(r.user)
    return r.user
  }
  const value = useMemo(() => ({
    user, loading, setUser,
    login: (email, password) => authenticate('/auth/login', { email, password }),
    register: (email, username, password) => authenticate('/auth/register', { email, username, password }),
    logout: () => { setToken(null); setUser(null) },
    refresh: () => api.get('/auth/me').then(setUser),
  }), [user, loading])
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

/* --------------------------------------------- watchlist + ratings (shared) */
const LibCtx = createContext(null)
export const useLibrary = () => useContext(LibCtx)

export function LibraryProvider({ children }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [watch, setWatch] = useState(new Set())
  const [ratings, setRatings] = useState(new Map())

  const reload = useCallback(async () => {
    const [w, r] = await Promise.all([api.get('/watchlist'), api.get('/ratings')]).catch(() => [[], []])
    setWatch(new Set(w.map((m) => m.id)))
    setRatings(new Map(r.map((m) => [m.id, m.user_rating])))
  }, [])

  useEffect(() => {
    if (!user) { setWatch(new Set()); setRatings(new Map()); return }
    reload()
  }, [user?.id])

  const needLogin = () => { toast('Sign in to save films and get recommendations', 'info'); navigate('/login'); }

  const toggleWatch = async (id, title) => {
    if (!user) return needLogin()
    const had = watch.has(id)
    setWatch((s) => { const n = new Set(s); had ? n.delete(id) : n.add(id); return n })
    try {
      await api.post(`/watchlist/${id}`)
      toast(had ? 'Removed from watchlist' : `${title ? title + ' added' : 'Added'} to watchlist`)
    } catch (e) {
      setWatch((s) => { const n = new Set(s); had ? n.add(id) : n.delete(id); return n })
      toast(e.message, 'error')
    }
  }

  const rate = async (id, value, review) => {
    if (!user) return needLogin()
    const prev = ratings.get(id)
    setRatings((m) => new Map(m).set(id, value))
    setWatch((s) => { const n = new Set(s); n.delete(id); return n })
    try {
      await api.put(`/ratings/${id}`, { value, review })
      toast(`Rated ${value} ${value === 1 ? 'star' : 'stars'}. Your picks are updated.`)
    } catch (e) {
      setRatings((m) => { const n = new Map(m); prev == null ? n.delete(id) : n.set(id, prev); return n })
      toast(e.message, 'error')
    }
  }

  const unrate = async (id) => {
    setRatings((m) => { const n = new Map(m); n.delete(id); return n })
    try { await api.del(`/ratings/${id}`); toast('Rating removed') } catch (e) { toast(e.message, 'error') }
  }

  return <LibCtx.Provider value={{ watch, ratings, toggleWatch, rate, unrate, reload }}>{children}</LibCtx.Provider>
}
