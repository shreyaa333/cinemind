import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Bookmark, Check, Clock } from 'lucide-react'
import { api, img } from '../api'
import { useAuth, useLibrary, useToast } from '../store.jsx'
import Stars from '../components/Stars.jsx'
import { MatchTicket, Rail } from '../components/Poster.jsx'
import { HBars } from '../components/Charts.jsx'

const SIGNALS = [
  ['collaborative', 'cf', 'People with similar taste', 'Viewers whose ratings resemble yours rated this highly'],
  ['content', 'content', 'Similar to films you rate', 'Shares themes, genres, cast and plot with your favourites'],
  ['genre_affinity', 'genre', 'Your favourite genres', 'Fits the genres you pick and rate highest'],
  ['popularity', 'popularity', 'Crowd and critic favourite', 'Well rated by critics and the community'],
]

export default function Movie() {
  const { id } = useParams()
  const { user } = useAuth()
  const { watch, ratings, toggleWatch, rate, unrate } = useLibrary()
  const toast = useToast()
  const nav = useNavigate()
  const [m, setM] = useState(null)
  const [similar, setSimilar] = useState([])
  const [review, setReview] = useState('')
  const [err, setErr] = useState('')

  const load = () => api.get(`/movies/${id}`).then((d) => { setM(d); setReview(d.user_review || '') }).catch(() => setErr('missing'))
  useEffect(() => { setM(null); setErr(''); window.scrollTo(0, 0); load(); api.get(`/movies/${id}/similar`).then(setSimilar) }, [id, user?.id])

  if (err) return <div className="page"><p className="error-text">We couldn’t find that film. <Link to="/browse">Browse all films</Link></p></div>
  if (!m) return <div className="detail"><div className="detail-bg sk" /></div>

  const mine = ratings.get(m.id)
  const saved = watch.has(m.id)
  const runtime = `${Math.floor(m.runtime / 60)}h ${m.runtime % 60}m`
  const signals = m.explain ? SIGNALS.map(([k, w, label, hint]) => ({ label, hint, value: m.explain.signals[k], weight: m.explain.weights[w] })) : null

  const saveReview = async () => { await rate(m.id, mine, review); load() }

  return (
    <>
      <section className="detail">
        <img className="detail-bg" src={img(m.backdrop)} alt="" />
        <div className="detail-shade" />
        <div className="detail-grid">
          <motion.img className="detail-poster" src={img(m.poster)} alt={`${m.title} poster`} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} />
          <div className="detail-info">
            <h1>{m.title}</h1>
            <div className="meta">
              <span>{m.year}</span><span><Clock size={14} /> {runtime}</span>
              <span>Directed by {m.director.split('|').join(' & ')}</span>
            </div>
            <div className="chips static">{m.genres.map((g) => <Link key={g} to={`/browse?genres=${g}`} className="chip">{g}</Link>)}</div>
            <p className="lead">{m.overview}</p>
            <p className="cast"><b>Starring</b> {m.cast.join(', ')}</p>

            <div className="scores">
              <div><b>{m.critic_rating.toFixed(1)}</b><span>Critics, out of 10</span></div>
              <div><b>{m.community_rating?.toFixed(1) ?? 'n/a'}</b><span>CineMind viewers, out of 5 ({m.rating_count})</span></div>
              {m.match != null && <div><MatchTicket value={m.match} large /><span>Your match</span></div>}
              {m.predicted_rating != null && <div><b>{m.predicted_rating}</b><span>We predict you’d give</span></div>}
            </div>

            <div className="actions">
              <button className={`btn ${saved ? 'ghost' : 'primary'}`} onClick={() => toggleWatch(m.id, m.title)}>
                {saved ? <><Check size={18} /> On your watchlist</> : <><Bookmark size={18} /> Add to watchlist</>}
              </button>
              <div className="rate-box">
                <span>{mine ? 'Your rating' : 'Rate this film'}</span>
                <Stars value={mine || 0} onChange={(v) => rate(m.id, v, review)} />
                {mine && <button className="link" onClick={() => unrate(m.id)}>Remove</button>}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className={`detail-lower ${signals || !user ? '' : 'single'}`}>
        {signals && (
          <section className="why panel">
            <h2>Why we picked this for you</h2>
            <p className="sub">{m.reason}. Each bar shows how strongly this film scores on a signal. The tag shows how much that signal counts for you right now.</p>
            <div className="signals">
              {signals.map((s, i) => (
                <div key={s.label} className="signal">
                  <div className="signal-top"><b>{s.label}</b><span className="wt">{Math.round(s.weight * 100)}% of your score</span></div>
                  <div className="beam"><motion.i initial={{ width: 0 }} animate={{ width: `${Math.max(3, s.value * 100)}%` }} transition={{ delay: 0.15 * i, duration: 0.8, ease: [0.16, 1, 0.3, 1] }} /></div>
                  <small>{s.hint}</small>
                </div>
              ))}
            </div>
          </section>
        )}
        {!user && <section className="panel why"><h2>Want to know if you’d like it?</h2><p className="sub">Sign in and rate a few films. We’ll show a personal match score and explain it.</p><Link className="btn primary" to="/login">Sign in</Link></section>}

        <section className="panel reviews">
          <h2>Reviews</h2>
          {user && mine && (
            <div className="write">
              <textarea value={review} onChange={(e) => setReview(e.target.value)} maxLength={1000} placeholder="What did you think? Share a few words." rows={3} aria-label="Your review" />
              <button className="btn small" onClick={saveReview}>{m.user_review ? 'Update review' : 'Post review'}</button>
            </div>
          )}
          {user && !mine && <p className="sub">Rate this film to write a review.</p>}
          {m.reviews.length === 0 ? <p className="sub">No reviews yet. Be the first.</p> : m.reviews.map((r, i) => (
            <article key={i} className="review">
              <span className="avatar sm" style={{ background: r.avatar_color }}>{r.username[0].toUpperCase()}</span>
              <div><div className="rv-top"><b>{r.username}</b><Stars value={r.rating} size={14} readOnly /></div><p>{r.review}</p></div>
            </article>
          ))}
        </section>
      </div>
      <div className="rows"><Rail title="More like this" subtitle="Similar themes, style and audience" items={similar} /></div>
    </>
  )
}
