import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Check } from 'lucide-react'
import { api, img } from '../api'
import { useAuth, useLibrary, useToast } from '../store.jsx'
import Stars from '../components/Stars.jsx'

export default function Onboarding() {
  const { refresh } = useAuth()
  const { reload } = useLibrary()
  const toast = useToast()
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [genres, setGenres] = useState([])
  const [all, setAll] = useState([])
  const [picks, setPicks] = useState([])
  const [ratings, setRatings] = useState({})
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.get('/genres').then((g) => setAll(g.filter((x) => x.count >= 5))); api.get('/recs/onboarding').then(setPicks) }, [])
  const count = Object.keys(ratings).length
  const toggle = (g) => setGenres((x) => (x.includes(g) ? x.filter((i) => i !== g) : [...x, g]))

  const finish = async () => {
    setBusy(true)
    try {
      await api.post('/profile/onboarding', { fav_genres: genres, ratings })
      await refresh()
      await reload()
      toast('All set. Your recommendations are ready.')
      nav('/', { replace: true })
    } catch (e) { toast(e.message, 'error'); setBusy(false) }
  }

  return (
    <div className="page onboard">
      <div className="steps" aria-label="Progress">
        {['Genres', 'Films'].map((s, i) => <span key={s} className={i <= step ? 'on' : ''}>{s}</span>)}
      </div>
      <AnimatePresence mode="wait">
        {step === 0 ? (
          <motion.section key="a" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
            <h1>What do you like to watch?</h1>
            <p className="sub">Pick at least three genres. You can change these any time from your profile.</p>
            <div className="genre-grid">
              {all.map((g) => (
                <button key={g.name} className={`genre ${genres.includes(g.name) ? 'on' : ''}`} onClick={() => toggle(g.name)} aria-pressed={genres.includes(g.name)}>
                  {genres.includes(g.name) && <Check size={16} />} {g.name}
                </button>
              ))}
            </div>
            <div className="onb-actions"><button className="btn primary" disabled={genres.length < 3} onClick={() => setStep(1)}>{genres.length < 3 ? `Pick ${3 - genres.length} more` : 'Continue'}</button></div>
          </motion.section>
        ) : (
          <motion.section key="b" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <h1>Rate films you’ve seen</h1>
            <p className="sub">Tap the stars under anything you’ve watched. Five or more gives noticeably better picks.</p>
            <div className="progress" aria-label={`${count} rated`}><i style={{ width: `${Math.min(100, (count / 5) * 100)}%` }} /></div>
            <div className="grid onb-grid">
              {picks.map((m) => (
                <div key={m.id} className={`onb-card ${ratings[m.id] ? 'rated' : ''}`}>
                  <img src={img(m.poster)} alt={`${m.title} poster`} />
                  <span className="t">{m.title}</span>
                  <Stars size={22} value={ratings[m.id] || 0} onChange={(v) => setRatings((r) => ({ ...r, [m.id]: v }))} />
                </div>
              ))}
            </div>
            <div className="onb-actions sticky">
              <button className="btn ghost" onClick={() => setStep(0)}>Back</button>
              <button className="btn primary" disabled={busy} onClick={finish}>{busy ? 'Building your feed…' : count ? `Finish with ${count} rated` : 'Skip for now'}</button>
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  )
}
