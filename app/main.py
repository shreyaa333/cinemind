import os
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import services
from .config import CORS_ORIGINS, DATA_DIR, ROOT
from .database import Base, SessionLocal, engine
from .models import Movie, Rating, User
from .routers import auth, library, movies, profile, recs
from .security import hash_password

DEMO = [  # (title, rating) -- a sci-fi / thriller flavoured taste so the demo account shows rich recommendations
    ("Inception", 5), ("Interstellar", 5), ("The Matrix", 4.5), ("Blade Runner 2049", 4.5), ("Arrival", 4.5),
    ("The Prestige", 5), ("Memento", 4.5), ("Ex Machina", 4), ("Dune", 4.5), ("The Dark Knight", 5),
    ("Mad Max: Fury Road", 4), ("Gravity", 3.5), ("Inglourious Basterds", 3), ("Frozen", 2), ("Barbie", 2),
]


def seed(db):
    if db.query(Movie).count() == 0:
        df = pd.read_csv(os.path.join(DATA_DIR, "movies.csv"))
        db.add_all([Movie(id=int(r.movie_id), title=r.title, year=int(r.year), genres=r.genres, director=r.director,
                          cast=r.cast, runtime=int(r.runtime), keywords=r.keywords, overview=r.overview,
                          critic_rating=float(r.avg_rating)) for r in df.itertuples()])
        db.commit()
    if not db.query(User).filter_by(email="demo@cinemind.dev").first():
        u = User(email="demo@cinemind.dev", username="Demo Viewer", password_hash=hash_password("demo1234"),
                 bio="Sci-fi devotee. Rewatching Nolan until the timeline makes sense.", avatar_color="#e50914",
                 fav_genres="Sci-Fi,Thriller,Mystery", onboarded=True, is_admin=True)
        db.add(u)
        db.commit()
        titles = {m.title: m.id for m in db.query(Movie).all()}
        for t, v in DEMO:
            if t in titles:
                db.add(Rating(user_id=u.id, movie_id=titles[t], value=v))
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
        services.load_catalogue(db)
    finally:
        db.close()
    services.load_recommender()
    yield


app = FastAPI(title="CineMind API", version="1.0.0",
              description="Hybrid (content-based + collaborative filtering) movie recommendation engine.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, movies.router, library.router, recs.router, profile.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return dict(status="ok", movies=len(services.state.movies), model_loaded=services.state.rec is not None)


# Serve the built React app (npm run build) from the same origin if present -> single-process deployment
DIST = os.path.join(ROOT, "..", "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = os.path.join(DIST, path)
        return FileResponse(f if path and os.path.isfile(f) else os.path.join(DIST, "index.html"))
