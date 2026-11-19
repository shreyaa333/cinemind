import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, ChevronLeft, ChevronRight, Plus, Star } from 'lucide-react'
import { img } from '../api'
import { useLibrary } from '../store.jsx'

export function MatchTicket({ value, large }) {
  if (value == null) return null
  return (
    <span className={`ticket ${large ? 'large' : ''}`} title="How well this fits your taste">
      <b>{value}%</b><i>match</i>
    </span>
  )
}

export function PosterCard({ movie, wide }) {
  const { watch, ratings, toggleWatch } = useLibrary()
  const saved = watch.has(movie.id)
  const mine = ratings.get(movie.id)
  const [loaded, setLoaded] = useState(false)
  return (
    <article className={`pcard ${wide ? 'wide' : ''}`}>
      <Link to={`/movie/${movie.id}`} className="pcard-link" aria-label={`${movie.title}, ${movie.year}`}>
        <div className={`pcard-img ${loaded ? 'ready' : ''}`}>
          <img src={img(movie.poster)} alt={`${movie.title} poster`} loading="lazy" onLoad={() => setLoaded(true)} />
          <MatchTicket value={movie.match} />
          {mine != null && <span className="mine"><Star size={12} fill="currentColor" /> {mine}</span>}
          <div className="pcard-over">
            {movie.reason && <p className="why">{movie.reason}</p>}
            <p className="gen">{movie.genres.slice(0, 3).join('  /  ')}</p>
          </div>
        </div>
        <div className="pcard-meta">
          <span className="t">{movie.title}</span>
          <span className="y">{movie.year}</span>
        </div>
      </Link>
      <button className={`wl ${saved ? 'on' : ''}`} onClick={() => toggleWatch(movie.id, movie.title)} aria-pressed={saved}
        aria-label={saved ? `Remove ${movie.title} from watchlist` : `Add ${movie.title} to watchlist`}>
        {saved ? <Check size={16} /> : <Plus size={16} />}
      </button>
    </article>
  )
}

export function Rail({ title, subtitle, items }) {
  const ref = useRef()
  const scroll = (dir) => ref.current?.scrollBy({ left: dir * ref.current.clientWidth * 0.85, behavior: 'smooth' })
  if (!items?.length) return null
  return (
    <section className="rail" aria-label={title}>
      <div className="rail-head">
        <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
        <div className="rail-btns">
          <button onClick={() => scroll(-1)} aria-label="Scroll left"><ChevronLeft size={18} /></button>
          <button onClick={() => scroll(1)} aria-label="Scroll right"><ChevronRight size={18} /></button>
        </div>
      </div>
      <div className="rail-track" ref={ref}>
        {items.map((m) => <PosterCard key={m.id} movie={m} />)}
      </div>
    </section>
  )
}

export function PosterGrid({ items }) {
  return <div className="grid">{items.map((m) => <PosterCard key={m.id} movie={m} />)}</div>
}

export function SkeletonRail() {
  return (
    <section className="rail">
      <div className="rail-head"><div><div className="sk sk-title" /></div></div>
      <div className="rail-track">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="pcard"><div className="pcard-img sk" /></div>)}</div>
    </section>
  )
}

export function Empty({ title, children, action }) {
  return (
    <div className="empty">
      <svg width="54" height="54" viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="6.5" fill="currentColor" opacity=".9" /><circle cx="16" cy="16" r="11.5" fill="none" stroke="currentColor" strokeOpacity=".4" strokeWidth="1.2" strokeDasharray="2 3.2" /></svg>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  )
}
