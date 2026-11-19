import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SlidersHorizontal, X } from 'lucide-react'
import { api, qs } from '../api'
import { useAuth } from '../store.jsx'
import { Empty, PosterGrid } from '../components/Poster.jsx'

const DECADES = [['2020', '2020s'], ['2010', '2010s'], ['2000', '2000s'], ['1990', '1990s'], ['1980', '1980s'], ['older', 'Before 1980']]
const RATINGS = [['7', '7+'], ['7.5', '7.5+'], ['8', '8+'], ['8.5', '8.5+']]
const RUNTIMES = [['100', 'Under 100 min'], ['120', 'Under 2 hours'], ['150', 'Under 2.5 hours']]

function decadeRange(d) {
  if (!d) return {}
  if (d === 'older') return { year_max: 1979 }
  return { year_min: +d, year_max: +d + 9 }
}

export default function Browse() {
  const { user } = useAuth()
  const [sp, setSp] = useSearchParams()
  const q = sp.get('q') || ''
  const genres = sp.get('genres')?.split(',').filter(Boolean) || []
  const decade = sp.get('decade') || ''
  const minr = sp.get('min') || ''
  const rt = sp.get('rt') || ''
  const sort = sp.get('sort') || (q ? 'relevance' : 'popular')

  const [allGenres, setAllGenres] = useState([])
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [panel, setPanel] = useState(false)

  useEffect(() => { api.get('/genres').then(setAllGenres) }, [])

  const query = useMemo(() => qs({ q, genres, ...decadeRange(decade), min_rating: minr, max_runtime: rt, sort }), [q, genres.join(), decade, minr, rt, sort])

  useEffect(() => {
    setLoading(true)
    api.get(`/movies?${query}&page=1&page_size=24`).then((r) => { setItems(r.items); setTotal(r.total); setPage(1) }).finally(() => setLoading(false))
  }, [query, user?.id])

  const more = () => api.get(`/movies?${query}&page=${page + 1}&page_size=24`).then((r) => { setItems((x) => [...x, ...r.items]); setPage(page + 1) })

  const set = (k, v) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n, { replace: true }) }
  const toggle = (k, cur, v) => set(k, cur === v ? '' : v)
  const toggleGenre = (g) => set('genres', (genres.includes(g) ? genres.filter((x) => x !== g) : [...genres, g]).join(','))
  const active = genres.length + (decade ? 1 : 0) + (minr ? 1 : 0) + (rt ? 1 : 0)
  const clear = () => setSp(q ? { q } : {}, { replace: true })

  const filters = (
    <div className="filters">
      <div className="f-head"><h3>Filters</h3>{active > 0 && <button className="link" onClick={clear}>Clear all</button>}</div>
      <fieldset><legend>Genre <small>(must match all)</small></legend>
        <div className="chips">{allGenres.map((g) => <button key={g.name} className={`chip ${genres.includes(g.name) ? 'on' : ''}`} onClick={() => toggleGenre(g.name)} aria-pressed={genres.includes(g.name)}>{g.name}</button>)}</div>
      </fieldset>
      <fieldset><legend>Decade</legend>
        <div className="chips">{DECADES.map(([v, l]) => <button key={v} className={`chip ${decade === v ? 'on' : ''}`} onClick={() => toggle('decade', decade, v)} aria-pressed={decade === v}>{l}</button>)}</div>
      </fieldset>
      <fieldset><legend>Critic score</legend>
        <div className="chips">{RATINGS.map(([v, l]) => <button key={v} className={`chip ${minr === v ? 'on' : ''}`} onClick={() => toggle('min', minr, v)} aria-pressed={minr === v}>{l}</button>)}</div>
      </fieldset>
      <fieldset><legend>Length</legend>
        <div className="chips">{RUNTIMES.map(([v, l]) => <button key={v} className={`chip ${rt === v ? 'on' : ''}`} onClick={() => toggle('rt', rt, v)} aria-pressed={rt === v}>{l}</button>)}</div>
      </fieldset>
    </div>
  )

  return (
    <div className="page browse">
      <div className="page-head">
        <div>
          <h1>{q ? <>Results for “{q}”</> : 'Browse films'}</h1>
          <p className="sub">{loading ? 'Searching…' : `${total} ${total === 1 ? 'film' : 'films'}`}</p>
        </div>
        <div className="head-tools">
          <button className="btn ghost small filter-toggle" onClick={() => setPanel(true)}><SlidersHorizontal size={16} /> Filters{active ? ` (${active})` : ''}</button>
          <label className="select">
            <span className="sr">Sort by</span>
            <select value={sort} onChange={(e) => set('sort', e.target.value)}>
              {q && <option value="relevance">Best match for search</option>}
              {user && <option value="match">Best match for you</option>}
              <option value="popular">Most popular</option>
              <option value="rating">Critic score</option>
              <option value="year_desc">Newest first</option>
              <option value="year_asc">Oldest first</option>
              <option value="title">Title A to Z</option>
              <option value="runtime">Shortest first</option>
            </select>
          </label>
        </div>
      </div>

      <div className="browse-layout">
        <aside className="side">{filters}</aside>
        {panel && (
          <div className="sheet" role="dialog" aria-modal="true" aria-label="Filters">
            <div className="sheet-body">
              <button className="icon-btn close" onClick={() => setPanel(false)} aria-label="Close filters"><X size={20} /></button>
              {filters}
              <button className="btn primary" onClick={() => setPanel(false)}>Show {total} films</button>
            </div>
          </div>
        )}
        <div className="results">
          {active > 0 && (
            <div className="active-chips">
              {genres.map((g) => <button key={g} className="chip on" onClick={() => toggleGenre(g)}>{g} <X size={13} /></button>)}
              {decade && <button className="chip on" onClick={() => set('decade', '')}>{DECADES.find((d) => d[0] === decade)?.[1]} <X size={13} /></button>}
              {minr && <button className="chip on" onClick={() => set('min', '')}>Critics {minr}+ <X size={13} /></button>}
              {rt && <button className="chip on" onClick={() => set('rt', '')}>{RUNTIMES.find((d) => d[0] === rt)?.[1]} <X size={13} /></button>}
            </div>
          )}
          {!loading && items.length === 0 ? (
            <Empty title="No films match those filters" action={<button className="btn ghost" onClick={clear}>Clear filters</button>}>
              Try removing a genre or widening the decade.
            </Empty>
          ) : (
            <>
              <PosterGrid items={items} />
              {items.length < total && <div className="more"><button className="btn ghost" onClick={more}>Show more films</button></div>}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
