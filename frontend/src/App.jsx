import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Navbar from './components/Navbar.jsx'
import { useAuth } from './store.jsx'
import Home from './pages/Home.jsx'
import Browse from './pages/Browse.jsx'
import ForYou from './pages/ForYou.jsx'
import Movie from './pages/Movie.jsx'
import Watchlist from './pages/Watchlist.jsx'
import Profile from './pages/Profile.jsx'
import Auth from './pages/Auth.jsx'
import Onboarding from './pages/Onboarding.jsx'
import About from './pages/About.jsx'

function Protected({ children }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <div className="splash" />
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />
  return children
}

function Footer() {
  return (
    <footer className="footer">
      <span>CineMind. Built with FastAPI, scikit-learn and React.</span>
      <span>Film data is a curated sample. Posters are generated artwork.</span>
    </footer>
  )
}

export default function App() {
  const loc = useLocation()
  const bare = ['/login', '/register'].includes(loc.pathname)
  return (
    <>
      {!bare && <Navbar />}
      <main>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={loc.pathname.split('/')[1] + (loc.pathname.startsWith('/movie') ? loc.pathname : '')} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}>
            <Routes location={loc}>
              <Route path="/" element={<Home />} />
              <Route path="/browse" element={<Browse />} />
              <Route path="/movie/:id" element={<Movie />} />
              <Route path="/about" element={<About />} />
              <Route path="/login" element={<Auth mode="login" />} />
              <Route path="/register" element={<Auth mode="register" />} />
              <Route path="/for-you" element={<Protected><ForYou /></Protected>} />
              <Route path="/watchlist" element={<Protected><Watchlist /></Protected>} />
              <Route path="/profile" element={<Protected><Profile /></Protected>} />
              <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
      {!bare && <Footer />}
    </>
  )
}
