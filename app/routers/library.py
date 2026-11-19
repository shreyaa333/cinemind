"""Ratings, reviews and watchlist."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..models import Rating, User, WatchlistItem
from ..security import current_user
from ..services import state

router = APIRouter(prefix="/api", tags=["library"])


class RatingIn(BaseModel):
    value: float = Field(ge=0.5, le=5.0)
    review: Optional[str] = Field(default="", max_length=1000)


@router.put("/ratings/{movie_id}")
def rate(movie_id: int, body: RatingIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if movie_id not in state.movies:
        raise HTTPException(404, "Movie not found")
    value = round(body.value * 2) / 2
    r = db.query(Rating).filter_by(user_id=user.id, movie_id=movie_id).first()
    if r:
        r.value = value
        if body.review is not None:
            r.review = body.review
    else:
        r = Rating(user_id=user.id, movie_id=movie_id, value=value, review=body.review or "")
        db.add(r)
    # rating a film removes it from the watchlist (it has been watched)
    wl = db.query(WatchlistItem).filter_by(user_id=user.id, movie_id=movie_id).first()
    if wl:
        db.delete(wl)
    db.commit()
    return dict(movie_id=movie_id, value=value, review=r.review)


@router.delete("/ratings/{movie_id}")
def unrate(movie_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.query(Rating).filter_by(user_id=user.id, movie_id=movie_id).delete()
    db.commit()
    return dict(ok=True)


@router.get("/ratings")
def my_ratings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Rating).filter_by(user_id=user.id).order_by(Rating.updated_at.desc()).all()
    watch = services.user_watchlist(db, user)
    ratings = {r.movie_id: r.value for r in rows}
    return [services.serialize(r.movie_id, ratings, watch, extra=dict(review=r.review, rated_at=r.updated_at.isoformat()), brief=True)
            for r in rows if r.movie_id in state.movies]


@router.get("/watchlist")
def get_watchlist(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(WatchlistItem).filter_by(user_id=user.id).order_by(WatchlistItem.added_at.desc()).all()
    ratings = services.user_ratings(db, user)
    ids = [r.movie_id for r in rows if r.movie_id in state.movies]
    recs = {s.movie_id: s for s in state.rec.recommend(ratings, services.fav_genres(user), n=len(state.movies), allowed=ids)} if ids else {}
    out = []
    for r in rows:
        if r.movie_id not in state.movies:
            continue
        extra = dict(added_at=r.added_at.isoformat())
        if r.movie_id in recs:
            extra["match"] = recs[r.movie_id].match
        out.append(services.serialize(r.movie_id, ratings, {r.movie_id}, extra=extra, brief=True))
    return out


@router.post("/watchlist/{movie_id}")
def toggle_watchlist(movie_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if movie_id not in state.movies:
        raise HTTPException(404, "Movie not found")
    row = db.query(WatchlistItem).filter_by(user_id=user.id, movie_id=movie_id).first()
    if row:
        db.delete(row)
        db.commit()
        return dict(movie_id=movie_id, in_watchlist=False)
    db.add(WatchlistItem(user_id=user.id, movie_id=movie_id))
    db.commit()
    return dict(movie_id=movie_id, in_watchlist=True)
