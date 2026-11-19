// Thin fetch wrapper. Token is kept in localStorage; a 401 triggers a global logout event.
const BASE = import.meta.env.VITE_API_URL || ''
const KEY = 'cinemind_token'

export const getToken = () => { try { return localStorage.getItem(KEY) } catch { return null } }
export const setToken = (t) => { try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY) } catch { /* private mode */ } }
export const img = (path) => (path?.startsWith('http') ? path : BASE + path)

async function req(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  const t = getToken()
  if (t) headers.Authorization = `Bearer ${t}`
  const res = await fetch(`${BASE}/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (res.status === 401 && t) window.dispatchEvent(new Event('cinemind:logout'))
  if (!res.ok) {
    let msg = res.statusText
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : j.detail?.[0]?.msg || msg
    } catch { /* non-JSON error */ }
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  get: (p) => req('GET', p),
  post: (p, b) => req('POST', p, b),
  put: (p, b) => req('PUT', p, b),
  del: (p) => req('DELETE', p),
}

export const qs = (obj) => {
  const p = new URLSearchParams()
  Object.entries(obj).forEach(([k, v]) => { if (v !== '' && v != null && !(Array.isArray(v) && !v.length)) p.set(k, Array.isArray(v) ? v.join(',') : v) })
  return p.toString()
}
