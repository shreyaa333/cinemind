import { motion } from 'framer-motion'

/** Taste radar: axes are your most-watched genres; the filled shape is how highly you rate them. */
export function Radar({ data, size = 320 }) {
  if (!data?.length) return null
  const n = data.length
  const c = size / 2
  const R = size / 2 - 74
  const pt = (i, v) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2
    return [c + Math.cos(a) * R * v, c + Math.sin(a) * R * v]
  }
  const poly = data.map((d, i) => pt(i, Math.max(d.affinity, 0.08)).join(',')).join(' ')
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="radar" role="img" aria-label="Genre taste radar">
      {[0.25, 0.5, 0.75, 1].map((r) => (
        <polygon key={r} points={data.map((_, i) => pt(i, r).join(',')).join(' ')} fill="none" stroke="var(--line)" />
      ))}
      {data.map((_, i) => <line key={i} x1={c} y1={c} x2={pt(i, 1)[0]} y2={pt(i, 1)[1]} stroke="var(--line)" />)}
      <motion.polygon points={poly} fill="var(--amber)" fillOpacity=".22" stroke="var(--amber)" strokeWidth="2" strokeLinejoin="round"
        initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }} style={{ transformOrigin: `${c}px ${c}px` }} transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }} />
      {data.map((d, i) => {
        const [x, y] = pt(i, Math.max(d.affinity, 0.08))
        const [lx, ly] = pt(i, 1.17)
        return (
          <g key={d.genre}>
            <circle cx={x} cy={y} r="3.5" fill="var(--amber)" />
            <text x={lx} y={ly} textAnchor={lx < c - 8 ? 'end' : lx > c + 8 ? 'start' : 'middle'} dominantBaseline="middle" fill="var(--muted)" fontSize="12">{d.genre}</text>
          </g>
        )
      })}
    </svg>
  )
}

export function Histogram({ data }) {
  const max = Math.max(1, ...data.map((d) => d.count))
  return (
    <div className="histo" role="img" aria-label="Distribution of your ratings">
      {data.map((d, i) => (
        <div key={d.rating} className="histo-col">
          <span className="histo-n">{d.count || ''}</span>
          <motion.div className="histo-bar" initial={{ height: 0 }} animate={{ height: `${(d.count / max) * 100}%` }} transition={{ delay: i * 0.04, duration: 0.6 }} />
          <span className="histo-l">{d.rating % 1 === 0 ? d.rating : ''}</span>
        </div>
      ))}
    </div>
  )
}

export function HBars({ rows, valueKey = 'count', labelKey, color = 'var(--teal)', fmt = (v) => v }) {
  const max = Math.max(0.0001, ...rows.map((r) => r[valueKey]))
  return (
    <div className="hbars">
      {rows.map((r, i) => (
        <div className="hbar" key={r[labelKey]}>
          <span className="hbar-l">{r[labelKey]}</span>
          <div className="hbar-track">
            <motion.div style={{ background: r.color || color }} initial={{ width: 0 }} animate={{ width: `${(r[valueKey] / max) * 100}%` }} transition={{ delay: i * 0.05, duration: 0.7, ease: [0.16, 1, 0.3, 1] }} />
          </div>
          <span className="hbar-v">{fmt(r[valueKey])}</span>
        </div>
      ))}
    </div>
  )
}
