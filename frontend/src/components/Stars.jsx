import { useState } from 'react'

const PATH = 'M12 2.6l2.8 5.9 6.4.9-4.7 4.5 1.2 6.4L12 17.2 6.3 20.3l1.2-6.4L2.8 9.4l6.4-.9z'

function Icon({ size, filled }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d={PATH} fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}

/** Half-star precision rating input. value 0.5..5; onChange(value). */
export default function Stars({ value = 0, onChange, size = 30, readOnly = false }) {
  const [hover, setHover] = useState(null)
  const shown = hover ?? value
  return (
    <div className="stars" onMouseLeave={() => setHover(null)} role={readOnly ? 'img' : 'radiogroup'} aria-label={`Rating ${value} out of 5`}>
      {[1, 2, 3, 4, 5].map((i) => {
        const fill = Math.max(0, Math.min(1, shown - (i - 1)))
        return (
          <span className="star" key={i} style={{ width: size, height: size }}>
            <span className="star-base"><Icon size={size} /></span>
            <span className="star-fill" style={{ width: `${fill * 100}%` }}><Icon size={size} filled /></span>
            {!readOnly && (
              <>
                <button type="button" className="half l" aria-label={`${i - 0.5} stars`} onMouseEnter={() => setHover(i - 0.5)} onFocus={() => setHover(i - 0.5)} onBlur={() => setHover(null)} onClick={() => onChange?.(i - 0.5)} />
                <button type="button" className="half r" aria-label={`${i} stars`} onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} onClick={() => onChange?.(i)} />
              </>
            )}
          </span>
        )
      })}
    </div>
  )
}
