# CineMind: Personalised Movie Recommendation System

A full-stack, ML-powered movie recommender with a cinematic dark UI. It uses a **hybrid recommender** (content-based TF-IDF + ALS matrix-factorisation collaborative filtering + a cold-start genre/popularity prior), a **FastAPI** backend with **SQLite/SQLAlchemy** and JWT auth, and a **React (Vite)** frontend.

| | |
|---|---|
| **ML** | scikit-learn, NumPy, SciPy, pandas. ALS is implemented from scratch with user/item biases. |
| **Backend** | FastAPI, SQLAlchemy 2, SQLite (swap to PostgreSQL via `DATABASE_URL`), bcrypt, PyJWT |
| **Frontend** | React 18, React Router, Framer Motion, hand-built SVG charts |
| **Tests** | 6 end-to-end API tests (pytest) |

## Quick start

**Requirements:** Python 3.10+, Node 18+.

### Option A: one command (Linux/macOS)
```bash
./run.sh          # installs deps, trains the model if needed, builds the UI, serves everything on :8000
```
Open **http://localhost:8000**. Demo login: `demo@cinemind.dev` / `demo1234`.

### Option B: manual / development mode (hot reload)
```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python data/build_dataset.py        # (optional) regenerate movies.csv + ratings.csv
python -m app.ml.train              # (optional) retrain + evaluate; a trained model is already included
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173 (proxies /api to :8000)
```
Interactive API docs: **http://localhost:8000/docs**

### Tests
```bash
cd backend && pytest -q
```

## Features

- **Hybrid personalised recommendations**: "Top picks for you", "Because you loved X", per-genre rows, hidden gems, trending
- **Match score** per film and a **"Why we picked this"** panel showing the four signals and their current weights
- **For You page** with a live switch between Hybrid / Collaborative / Content / Popularity so you can compare engines
- **Search** with typo tolerance (`inceptoin` finds Inception), live autocomplete, search by title, director, actor, keyword
- **Filters:** multi-genre, decade, critic score, runtime; sort by popularity, critics, year, title, or *best match for you*
- **Half-star ratings and reviews**; ratings change recommendations instantly (no retraining, see below)
- **Watchlist** (rating a film removes it), **profile** with taste radar, rating histogram, genre/decade/director stats, persona title, editable bio/avatar/genres
- **Onboarding** for new users (pick genres, rate films) solves the cold-start problem
- **"How it works" page** shows the real evaluation metrics from the last training run
- Responsive down to phones, keyboard-accessible, respects reduced-motion

## How the recommender works

`backend/app/ml/recommender.py`

1. **Content-based.** Each film becomes a TF-IDF vector from four weighted blocks: genres (1.0), keywords (0.8), director+cast (0.55), plot overview with bigrams (0.45). A user taste profile is the rating-weighted mean of liked films (dislikes push away at 0.35 strength). Candidates are ranked by cosine similarity.
2. **Collaborative filtering.** Biased matrix factorisation `r̂ = μ + bᵤ + bᵢ + pᵤ·qᵢ` trained with **Alternating Least Squares** (closed-form ridge solves). Item factors are learned offline. For a *live* user the vector `pᵤ` is obtained by a closed-form **fold-in** from their ratings, so a new rating changes recommendations on the next request.
3. **Cold-start prior.** Bayesian-damped rating + log-popularity + critic score, plus a genre-affinity vector from onboarding picks and ratings.
4. **Adaptive blend.** With `n` ratings, `α = 1 − e^(−n/10)`. Weights: CF `0.50α`, content `0.25α`, genre prior `0.35(1−α)+0.05`, popularity gets the remainder. New users see popular + their genres; established users see mostly personalised signals.

### Evaluation (hold-out of 20% of each user's ratings, run `python -m app.ml.train`)

| Method | NDCG@10 | Hit-rate@10 | Catalogue coverage |
|---|---|---|---|
| Random | 0.053 | 25% | 100% |
| Popularity | 0.099 | 42% | 12% |
| Content-based | 0.130 | 50% | 98% |
| Collaborative (ALS) | 0.141 | 52% | 64% |
| **Hybrid** | **0.157** | **56%** | 68% |

Rating prediction RMSE: global mean 0.686 → film mean 0.661 → biases only 0.636 → **ALS 0.584**. Hyper-parameters (k ∈ {4,8,16,24}, λ ∈ {4,8,14}) are chosen on a validation split.

> **Important: about the data.** The 164 films are a real, hand-curated catalogue (original short plot summaries, real directors/casts). The **600 users' ratings are synthetic**: generated from hidden taste personas plus noise (`data/build_dataset.py`), because real rating datasets can't be bundled. The metrics therefore show the pipeline works and that the hybrid beats its parts. They are **not** a claim about real-world accuracy. To report real numbers, plug in MovieLens (below). Posters are generated SVG artwork, not studio posters.

### Swapping in a real dataset (e.g. MovieLens)
1. Produce `backend/data/movies.csv` with columns `movie_id,title,year,genres,director,cast,runtime,keywords,overview,avg_rating` (genres/cast/keywords are `|`-separated) and `ratings.csv` with `user_id,movie_id,rating` (0.5–5).
2. Delete `backend/cinemind.db`, run `python -m app.ml.train`, restart the server.
3. For real posters, store a TMDB poster URL per movie and return it from `services.serialize` instead of `/api/posters/{id}.svg`.

An admin account (the demo user) can call `POST /api/system/retrain` (or use the button on the "How it works" page) to fold real users' ratings into the model.

## Project structure

```
cinemind/
├── run.sh                         one-command launcher
├── backend/
│   ├── requirements.txt  .env.example
│   ├── data/                      build_dataset.py, movies.csv, ratings.csv
│   ├── models/                    recommender.pkl, metrics.json  (output of training)
│   ├── tests/test_api.py
│   └── app/
│       ├── main.py                app factory, seeding, serves built frontend
│       ├── config.py database.py models.py security.py
│       ├── services.py            catalogue cache, search, serialisers, retrain
│       ├── posters.py             procedural poster/backdrop SVG generator
│       ├── ml/recommender.py      content + ALS + hybrid engine
│       ├── ml/train.py            tuning, evaluation, final fit
│       └── routers/               auth, movies, library, recs, profile
└── frontend/
    ├── package.json vite.config.js index.html
    └── src/
        ├── main.jsx App.jsx api.js store.jsx index.css
        ├── components/            Navbar, Hero, Poster (card/rail/grid), Stars, Charts
        └── pages/                 Home, Browse, ForYou, Movie, Watchlist, Profile, Auth, Onboarding, About
```

## API overview

| Method & path | Purpose |
|---|---|
| `POST /api/auth/register` · `/login` · `GET /api/auth/me` | JWT auth |
| `GET /api/movies?q=&genres=&year_min=&year_max=&min_rating=&max_runtime=&sort=&page=` | search, filter, sort (`sort=match` is personalised) |
| `GET /api/movies/{id}` · `/similar` · `/api/search/suggest?q=` | detail (with explanation), similar films, autocomplete |
| `PUT/DELETE /api/ratings/{id}` · `GET /api/ratings` | ratings + reviews |
| `POST /api/watchlist/{id}` (toggle) · `GET /api/watchlist` | watchlist |
| `GET /api/recs/home` · `/for-you?mode=hybrid\|cf\|content\|popularity` · `/onboarding` | recommendation feeds |
| `GET /api/profile/stats` · `PUT /api/profile` · `POST /api/profile/onboarding` | profile |
| `GET /api/system/metrics` · `POST /api/system/retrain` (admin) | model evaluation, retraining |

## Production notes
Set a strong `SECRET_KEY`, restrict `CORS_ORIGINS`, and set `DATABASE_URL` to PostgreSQL. The retrain job runs in-process, so use a task queue (Celery/RQ) for large datasets. The similarity matrices are dense (O(items²)); beyond ~20k films switch to approximate nearest neighbours (Faiss/Annoy).
