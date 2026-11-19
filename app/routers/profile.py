import json
import os
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import services
from ..config import MODEL_DIR
from ..database import SessionLocal, get_db
from ..models import Rating, User, WatchlistItem
from ..security import current_user
from ..services import state
from .auth import user_out

router = APIRouter(prefix="/api", tags=["profile"])


class ProfileIn(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=40)
    bio: Optional[str] = Field(default=None, max_length=280)
    avatar_color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    fav_genres: Optional[List[str]] = None


class OnboardIn(BaseModel):
    fav_genres: List[str] = []
    ratings: dict[int, float] = {}


@router.put("/profile")
def update_profile(body: ProfileIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.username is not None:
        user.username = body.username.strip()
    if body.bio is not None:
        user.bio = body.bio
    if body.avatar_color is not None:
        user.avatar_color = body.avatar_color
    if body.fav_genres is not None:
        user.fav_genres = ",".join(g for g in body.fav_genres if g)
    db.commit()
    return user_out(user)


@router.post("/profile/onboarding")
def onboarding(body: OnboardIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.fav_genres = ",".join(g for g in body.fav_genres if g)
    for mid, val in body.ratings.items():
        if mid in state.movies and 0.5 <= val <= 5:
            r = db.query(Rating).filter_by(user_id=user.id, movie_id=mid).first()
            if r:
                r.value = round(val * 2) / 2
            else:
                db.add(Rating(user_id=user.id, movie_id=mid, value=round(val * 2) / 2))
    user.onboarded = True
    db.commit()
    return user_out(user)


@router.get("/profile/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Rating).filter_by(user_id=user.id).all()
    ratings = {r.movie_id: r.value for r in rows}
    wl = db.query(WatchlistItem).filter_by(user_id=user.id).count()
    hist = Counter(r.value for r in rows)
    genre_counts, directors, decades = Counter(), Counter(), Counter()
    minutes = 0
    for r in rows:
        m = state.movies.get(r.movie_id)
        if not m:
            continue
        minutes += m["runtime"]
        for g in m["genres"]:
            genre_counts[g] += 1
        if r.value >= 3.5:
            for d in m["director"].split("|"):
                directors[d] += 1
        decades[f"{m['year'] // 10 * 10}s"] += 1
    taste = state.rec.taste_vector(ratings)
    # Taste radar: blend of affinity (mean rating) and share of watched films
    top_genres = [g for g, _ in genre_counts.most_common(8)]
    radar = [dict(genre=g, affinity=round(taste.get(g, 0), 2), share=round(genre_counts[g] / max(len(rows), 1), 2)) for g in top_genres]
    persona = None
    if rows:
        g0 = genre_counts.most_common(1)[0][0]
        persona = {
            "Sci-Fi": "The Futurist", "Action": "The Adrenaline Seeker", "Drama": "The Cinephile", "Comedy": "The Joy Seeker",
            "Horror": "The Fearless", "Thriller": "The Edge Rider", "Crime": "The Noir Detective", "Romance": "The Hopeless Romantic",
            "Animation": "The Dreamer", "Fantasy": "The Wanderer", "Adventure": "The Explorer", "Mystery": "The Puzzle Solver",
        }.get(g0, "The Film Buff")
    return dict(
        rated=len(rows), watchlist=wl, hours_watched=round(minutes / 60, 1),
        avg_rating=round(sum(ratings.values()) / len(ratings), 2) if ratings else None,
        histogram=[dict(rating=k, count=hist.get(k, 0)) for k in [0.5 * i for i in range(1, 11)]],
        genres=[dict(genre=g, count=c) for g, c in genre_counts.most_common(10)],
        decades=sorted([dict(decade=d, count=c) for d, c in decades.items()], key=lambda x: x["decade"]),
        top_directors=[dict(name=d, count=c) for d, c in directors.most_common(5)],
        radar=radar, persona=persona,
    )


@router.get("/system/metrics")
def metrics():
    path = os.path.join(MODEL_DIR, "metrics.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Model not evaluated yet. Run: python -m app.ml.train")
    with open(path) as f:
        data = json.load(f)
    data["model"] = dict(factors=state.rec.k, regularisation=state.rec.lam, items=state.rec.n_items)
    return data


@router.post("/system/retrain")
def retrain(tasks: BackgroundTasks, user: User = Depends(current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Admin only")

    def job():
        db = SessionLocal()
        try:
            services.retrain(db)
        finally:
            db.close()

    tasks.add_task(job)
    return dict(status="retraining started")
