import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Pencil, X } from 'lucide-react'
import { api } from '../api'
import { useAuth, useLibrary, useToast } from '../store.jsx'
import { Empty, PosterGrid } from '../components/Poster.jsx'
import { HBars, Histogram, Radar } from '../components/Charts.jsx'

const SWATCHES = ['#e50914', '#f0a84b', '#43c1b0', '#6366f1', '#ec4899', '#22c55e', '#0ea5e9', '#a855f7']

function EditDialog({ user, genres, onClose, onSaved }) {
  const toast = useToast()
  const [f, setF] = useState({ username: user.username, bio: user.bio, avatar_color: user.avatar_color, fav_genres: user.fav_genres })
  const [busy, setBusy] = useState(false)
  const save = async (e) => {
    e.preventDefault(); setBusy(true)
    try { onSaved(await api.put('/profile', f)); toast('Profile saved'); onClose() } catch (er) { toast(er.message, 'error'); setBusy(false) }
  }
  const tog = (g) => setF((x) => ({ ...x, fav_genres: x.fav_genres.includes(g) ? x.fav_genres.filter((i) => i !== g) : [...x.fav_genres, g] }))
  return (
    <div className="modal" role="dialog" aria-modal="true" aria-label="Edit profile" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal-body" onSubmit={save}>
        <button type="button" className="icon-btn close" onClick={onClose} aria-label="Close"><X size={20} /></button>
        <h2>Edit profile</h2>
        <label>Display name<input value={f.username} minLength={2} maxLength={40} required onChange={(e) => setF({ ...f, username: e.target.value })} /></label>
        <label>Bio<textarea rows={3} maxLength={280} value={f.bio} onChange={(e) => setF({ ...f, bio: e.target.value })} /></label>
        <fieldset><legend>Avatar colour</legend>
          <div className="swatches">{SWATCHES.map((c) => <button type="button" key={c} style={{ background: c }} className={f.avatar_color === c ? 'on' : ''} aria-label={c} onClick={() => setF({ ...f, avatar_color: c })} />)}</div>
        </fieldset>
        <fieldset><legend>Favourite genres <small>(used for recommendations)</small></legend>
          <div className="chips">{genres.map((g) => <button type="button" key={g.name} className={`chip ${f.fav_genres.includes(g.name) ? 'on' : ''}`} onClick={() => tog(g.name)}>{g.name}</button>)}</div>
        </fieldset>
        <button className="btn primary" disabled={busy}>Save changes</button>
      </form>
    </div>
  )
}

export default function Profile() {
  const { user, setUser } = useAuth()
  const { ratings } = useLibrary()
  const [stats, setStats] = useState(null)
  const [rated, setRated] = useState(null)
  const [genres, setGenres] = useState([])
  const [edit, setEdit] = useState(false)
  const [tab, setTab] = useState('rated')

  useEffect(() => { api.get('/profile/stats').then(setStats); api.get('/ratings').then(setRated); api.get('/genres').then(setGenres) }, [ratings.size])

  return (
    <div className="page profile">
      <header className="p-head">
        <span className="avatar xl" style={{ background: user.avatar_color }}>{user.username[0].toUpperCase()}</span>
        <div>
          <h1>{user.username}</h1>
          {stats?.persona && <p className="persona">{stats.persona}</p>}
          <p className="bio">{user.bio || 'Add a short bio so people know your taste.'}</p>
          <div className="chips static">{user.fav_genres.map((g) => <span key={g} className="chip on">{g}</span>)}</div>
        </div>
        <button className="btn ghost small" onClick={() => setEdit(true)}><Pencil size={15} /> Edit profile</button>
      </header>

      {stats && (
        <>
          <div className="stat-row">
            <div><b>{stats.rated}</b><span>Films rated</span></div>
            <div><b>{stats.avg_rating ?? 'n/a'}</b><span>Average rating</span></div>
            <div><b>{stats.hours_watched}</b><span>Hours watched</span></div>
            <div><b>{stats.watchlist}</b><span>On watchlist</span></div>
          </div>

          {stats.rated > 0 ? (
            <div className="charts">
              <section className="panel"><h2>Your taste</h2><p className="sub">How highly you rate your most-watched genres.</p><Radar data={stats.radar} /></section>
              <section className="panel"><h2>How you rate</h2><p className="sub">Number of films at each star rating.</p><Histogram data={stats.histogram} />
                <h3 className="mt">Watched by decade</h3><HBars rows={stats.decades} labelKey="decade" /></section>
              <section className="panel"><h2>Genres you watch</h2><HBars rows={stats.genres} labelKey="genre" color="var(--amber)" />
                {stats.top_directors.length > 0 && <><h3 className="mt">Directors you rate highly</h3><HBars rows={stats.top_directors} labelKey="name" /></>}</section>
            </div>
          ) : <Empty title="No ratings yet" action={<Link className="btn primary" to="/browse">Find films to rate</Link>}>Rate films and your taste profile appears here.</Empty>}
        </>
      )}

      {rated?.length > 0 && (
        <section className="rated">
          <div className="seg small" role="tablist">
            <button className={tab === 'rated' ? 'on' : ''} onClick={() => setTab('rated')}>Rated films ({rated.length})</button>
            <button className={tab === 'reviews' ? 'on' : ''} onClick={() => setTab('reviews')}>Your reviews ({rated.filter((r) => r.review).length})</button>
          </div>
          {tab === 'rated' ? <PosterGrid items={rated} /> : (
            <div className="reviews-list">{rated.filter((r) => r.review).map((r) => (
              <Link to={`/movie/${r.id}`} key={r.id} className="rv-item"><b>{r.title}</b><span>{r.user_rating} / 5</span><p>{r.review}</p></Link>
            ))}{!rated.some((r) => r.review) && <p className="sub">You haven’t written any reviews. Open a film you’ve rated to add one.</p>}</div>
          )}
        </section>
      )}
      {edit && <EditDialog user={user} genres={genres} onClose={() => setEdit(false)} onSaved={setUser} />}
    </div>
  )
}
