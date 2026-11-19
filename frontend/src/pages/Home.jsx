import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../store.jsx'
import Hero from '../components/Hero.jsx'
import { Rail, SkeletonRail } from '../components/Poster.jsx'

export default function Home() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null)
    api.get('/recs/home').then(setData).catch((e) => setError(e.message))
  }, [user?.id])

  if (error) return <div className="page"><p className="error-text">Couldn’t load recommendations: {error}. Is the API running on port 8000?</p></div>
  return (
    <>
      <Hero movie={data?.hero} />
      <div className="rows">
        {!data && <><SkeletonRail /><SkeletonRail /></>}
        {data && !user && (
          <aside className="cta-band">
            <div>
              <h2>Rate a few films and we’ll tune everything to you</h2>
              <p>Create a free account and the rows below become your own: ranked by taste, not by what’s popular.</p>
            </div>
            <Link to="/register" className="btn primary">Create free account</Link>
          </aside>
        )}
        {data?.rows.map((r) => <Rail key={r.title} title={r.title} subtitle={r.subtitle} items={r.items} />)}
      </div>
    </>
  )
}
