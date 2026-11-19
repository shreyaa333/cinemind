import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useLibrary } from '../store.jsx'
import { Empty, PosterGrid } from '../components/Poster.jsx'

export default function Watchlist() {
  const { watch } = useLibrary()
  const [items, setItems] = useState(null)
  const [sort, setSort] = useState('match')

  useEffect(() => { api.get('/watchlist').then(setItems) }, [])
  // keep list in sync when the user removes something from a card
  const shown = (items || []).filter((m) => watch.has(m.id)).sort((a, b) =>
    sort === 'match' ? (b.match ?? 0) - (a.match ?? 0) : sort === 'recent' ? (b.added_at > a.added_at ? 1 : -1) : sort === 'runtime' ? a.runtime - b.runtime : b.critic_rating - a.critic_rating)

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Your watchlist</h1><p className="sub">{items ? `${shown.length} ${shown.length === 1 ? 'film' : 'films'} saved` : ' '}</p></div>
        <label className="select"><span className="sr">Sort by</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="match">Best match for you</option><option value="recent">Recently added</option>
            <option value="rating">Critic score</option><option value="runtime">Shortest first</option>
          </select>
        </label>
      </div>
      {!items ? null : shown.length ? <PosterGrid items={shown} />
        : <Empty title="Your watchlist is empty" action={<Link className="btn primary" to="/browse">Find something to watch</Link>}>Tap the + on any poster to save it for later.</Empty>}
    </div>
  )
}
