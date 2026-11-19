import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Bookmark, Check, Info } from 'lucide-react'
import { img } from '../api'
import { useLibrary } from '../store.jsx'
import { MatchTicket } from './Poster.jsx'

const fmtRuntime = (m) => `${Math.floor(m / 60)}h ${m % 60}m`

// The one orchestrated moment of the app: title lines rise out of a mask, then the rest fades in.
const line = { hidden: { y: '110%' }, show: { y: 0, transition: { duration: 0.9, ease: [0.16, 1, 0.3, 1] } } }
const fade = (d) => ({ hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { delay: d, duration: 0.6, ease: 'easeOut' } } })

export default function Hero({ movie }) {
  const { watch, toggleWatch } = useLibrary()
  if (!movie) return <div className="hero sk" />
  const saved = watch.has(movie.id)
  const words = movie.title.split(' ')
  const mid = Math.ceil(words.length / 2)
  const lines = movie.title.length > 16 ? [words.slice(0, mid).join(' '), words.slice(mid).join(' ')] : [movie.title]
  return (
    <section className="hero" aria-label="Featured recommendation">
      <img className="hero-bg" src={img(movie.backdrop)} alt="" />
      <div className="hero-shade" />
      <motion.div className="hero-content" initial="hidden" animate="show" key={movie.id} variants={{ show: { transition: { staggerChildren: 0.12 } } }}>
        <motion.div className="hero-kicker" variants={fade(0)}>
          <MatchTicket value={movie.match} large />
          <span>{movie.reason}</span>
        </motion.div>
        <h1 className="hero-title" aria-label={movie.title}>
          {lines.map((l, i) => <span className="mask" key={i}><motion.span variants={line}>{l}</motion.span></span>)}
        </h1>
        <motion.div className="meta" variants={fade(0.35)}>
          <span>{movie.year}</span><span>{fmtRuntime(movie.runtime)}</span>
          <span>{movie.genres.slice(0, 3).join(', ')}</span>
          <span>Directed by {movie.director.split('|')[0]}</span>
        </motion.div>
        <motion.p className="hero-over" variants={fade(0.45)}>{movie.overview}</motion.p>
        <motion.div className="hero-actions" variants={fade(0.55)}>
          <Link className="btn primary" to={`/movie/${movie.id}`}><Info size={18} /> See details</Link>
          <button className="btn ghost" onClick={() => toggleWatch(movie.id, movie.title)}>
            {saved ? <><Check size={18} /> On your watchlist</> : <><Bookmark size={18} /> Add to watchlist</>}
          </button>
        </motion.div>
      </motion.div>
      <motion.img className="hero-poster" src={img(movie.poster)} alt={`${movie.title} poster`}
        initial={{ opacity: 0, x: 40, rotate: 2 }} animate={{ opacity: 1, x: 0, rotate: 1.5 }} transition={{ delay: 0.5, duration: 0.9, ease: [0.16, 1, 0.3, 1] }} />
    </section>
  )
}
