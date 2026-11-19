import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, img } from '../api'
import { useAuth, useToast } from '../store.jsx'
import { Logo } from '../components/Navbar.jsx'

export default function Auth({ mode }) {
  const register = mode === 'register'
  const { login, register: signUp } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const toast = useToast()
  const [f, setF] = useState({ email: '', username: '', password: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [wall, setWall] = useState([])

  useEffect(() => { api.get('/movies?sort=rating&page_size=24').then((r) => setWall(r.items)) }, [])
  useEffect(() => setErr(''), [mode])

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      const u = register ? await signUp(f.email, f.username, f.password) : await login(f.email, f.password)
      toast(register ? `Welcome to CineMind, ${u.username}` : `Welcome back, ${u.username}`)
      nav(!u.onboarded ? '/onboarding' : loc.state?.from || '/', { replace: true })
    } catch (e2) { setErr(e2.message) } finally { setBusy(false) }
  }
  const demo = () => setF({ ...f, email: 'demo@cinemind.dev', password: 'demo1234' })

  return (
    <div className="auth">
      <div className="auth-wall" aria-hidden="true">
        <div className="wall-grid">{wall.map((m, i) => <img key={m.id} src={img(m.poster)} alt="" style={{ animationDelay: `${(i % 8) * 0.07}s` }} />)}</div>
        <div className="wall-shade" />
        <p className="wall-quote">Every film you rate teaches us what to show you next.</p>
      </div>
      <div className="auth-panel">
        <Logo />
        <form onSubmit={submit} className="auth-form">
          <h1>{register ? 'Create your account' : 'Welcome back'}</h1>
          <p className="sub">{register ? 'Free, and takes under a minute.' : 'Sign in to see your recommendations.'}</p>
          {register && <label>Display name<input required minLength={2} maxLength={40} value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} autoComplete="nickname" /></label>}
          <label>Email<input required type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} autoComplete="email" /></label>
          <label>Password<input required type="password" minLength={6} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete={register ? 'new-password' : 'current-password'} /></label>
          {err && <p className="error-text" role="alert">{err}</p>}
          <button className="btn primary block" disabled={busy}>{busy ? 'One moment…' : register ? 'Create account' : 'Sign in'}</button>
          {!register && <button type="button" className="btn ghost block" onClick={demo}>Use the demo account</button>}
          <p className="switch">{register ? <>Already a member? <Link to="/login">Sign in</Link></> : <>New here? <Link to="/register">Create an account</Link></>}</p>
        </form>
      </div>
    </div>
  )
}
