import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth, useToast } from '../store.jsx'
import { HBars } from '../components/Charts.jsx'

const NAMES = { random: 'Random', popularity: 'Popularity', content: 'Content-based', cf: 'Collaborative', hybrid: 'CineMind hybrid' }
const COLORS = { random: 'var(--faint)', popularity: 'var(--faint)', content: 'var(--teal)', cf: 'var(--teal)', hybrid: 'var(--amber)' }

export default function About() {
  const { user } = useAuth()
  const toast = useToast()
  const [m, setM] = useState(null)
  useEffect(() => { api.get('/system/metrics').then(setM).catch(() => {}) }, [])

  const rows = (key) => m ? Object.entries(m.ranking).map(([k, v]) => ({ name: NAMES[k], value: v[key], color: COLORS[k] })) : []
  const rmse = m ? Object.entries(m.rating_prediction).map(([k, v]) => ({ name: { global_mean: 'Global average', item_mean: 'Film average', bias_only: 'Biases only', als: 'Matrix factorisation' }[k], value: v.rmse, color: k === 'als' ? 'var(--amber)' : 'var(--faint)' })) : []

  return (
    <div className="page about">
      <div className="page-head"><div><h1>How CineMind picks your films</h1><p className="sub">Three models, blended. Here’s what each does and how well it works.</p></div></div>

      <div className="method">
        <article className="panel"><h2>Content-based</h2><p>Every film becomes a TF-IDF vector built from its genres, themes, cast, director and plot. Your taste profile is the rating-weighted average of the films you liked. We rank films by cosine similarity to it.</p><code>score = cos(profile, film)</code></article>
        <article className="panel"><h2>Collaborative filtering</h2><p>Alternating Least Squares learns hidden taste factors from {m?.dataset.users ?? '600'} viewers’ ratings. A new rating updates your vector instantly through a closed-form ridge solve, with no retraining.</p><code>r̂ = μ + bᵤ + bᵢ + pᵤ · qᵢ</code></article>
        <article className="panel"><h2>Hybrid blend</h2><p>Weights adapt to how much you’ve rated. New users get genre picks and popularity; established users get mostly collaborative and content signals. This solves the cold-start problem.</p><code>α = 1 − e^(−n/10)</code></article>
      </div>

      {m && (
        <div className="eval">
          <section className="panel">
            <h2>Ranking quality</h2><p className="sub">NDCG@10 on held-out ratings from {m.ranking.hybrid.users_evaluated} users. Higher is better.</p>
            <HBars rows={rows('ndcg_at_10')} labelKey="name" valueKey="value" fmt={(v) => v.toFixed(3)} />
            <h3 className="mt">Hit rate @10</h3>
            <HBars rows={rows('hit_rate_at_10')} labelKey="name" valueKey="value" fmt={(v) => `${Math.round(v * 100)}%`} />
          </section>
          <section className="panel">
            <h2>Rating prediction error</h2><p className="sub">RMSE on 20% held-out ratings. Lower is better.</p>
            <HBars rows={rmse} labelKey="name" valueKey="value" fmt={(v) => v.toFixed(3)} />
            <h3 className="mt">Dataset</h3>
            <dl className="facts"><div><dt>Films</dt><dd>{m.dataset.movies}</dd></div><div><dt>Ratings</dt><dd>{m.dataset.ratings.toLocaleString()}</dd></div><div><dt>Viewers</dt><dd>{m.dataset.users}</dd></div><div><dt>Best factors (k)</dt><dd>{m.best_params.k}</dd></div></dl>
            {user?.is_admin && <button className="btn ghost small" onClick={() => api.post('/system/retrain').then(() => toast('Retraining on live ratings')).catch((e) => toast(e.message, 'error'))}>Retrain with live ratings</button>}
          </section>
        </div>
      )}
    </div>
  )
}
