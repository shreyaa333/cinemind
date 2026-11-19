import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../store.jsx'
import { Empty, PosterGrid } from '../components/Poster.jsx'

const MODES = [
  { id: 'hybrid', label: 'Hybrid', text: 'Blends all three signals below. The weights shift toward you as you rate more films.' },
  { id: 'cf', label: 'People like you', text: 'Collaborative filtering: matrix factorisation finds viewers with ratings patterns close to yours and surfaces what they loved.' },
  { id: 'content', label: 'Similar to your taste', text: 'Content-based: compares genres, themes, cast, directors and plot text with the films you rated highly.' },
  { id: 'popularity', label: 'Most popular', text: 'No personalisation. The baseline every other mode has to beat.' },
]

export default function ForYou() {
  const { user } = useAuth()
  const [mode, setMode] = useState('hybrid')
  const [items, setItems] = useState(null)

  useEffect(() => {
    setItems(null)
    api.get(`/recs/for-you?n=36&mode=${mode}`).then(setItems)
  }, [mode, user?.id])

  const current = MODES.find((m) => m.id === mode)
  return (
    <div className="page">
      <div className="page-head"><div><h1>Picked for you</h1><p className="sub">Switch the engine to see how each approach ranks your films.</p></div></div>
      <div className="seg" role="tablist">
        {MODES.map((m) => <button key={m.id} role="tab" aria-selected={mode === m.id} className={mode === m.id ? 'on' : ''} onClick={() => setMode(m.id)}>{m.label}</button>)}
      </div>
      <p className="mode-text">{current.text}</p>
      {!items ? <div className="grid">{Array.from({ length: 12 }).map((_, i) => <div key={i} className="pcard"><div className="pcard-img sk" /></div>)}</div>
        : items.length ? <PosterGrid items={items} />
        : <Empty title="Nothing to recommend yet" action={<Link className="btn primary" to="/browse">Browse films</Link>}>Rate some films and this page fills up.</Empty>}
    </div>
  )
}
