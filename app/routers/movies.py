from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from .. import posters, services
from ..database import get_db
from ..models import Rating, User
from ..security import optional_user
from ..services import state

router = APIRouter(prefix="/api", tags=["movies"])


@router.get("/posters/{movie_id}.svg")
def poster(movie_id: int):
    m = state.movies.get(movie_id)
    if not m:
        raise HTTPException(404)
    return Response(posters.poster_svg(m), media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/posters/{movie_id}/backdrop.svg")
def backdrop(movie_id: int):
    m = state.movies.get(movie_id)
    if not m:
        raise HTTPException(404)
    return Response(posters.backdrop_svg(m), media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/genres")
def genres():
    counts = {}
    for m in state.movies.values():
        for g in m["genres"]:
            counts[g] = counts.get(g, 0) + 1
    return [dict(name=g, count=c) for g, c in sorted(counts.items(), key=lambda x: -x[1])]


@router.get("/movies")
def list_movies(
    q: Optional[str] = None,
    genres: Optional[str] = Query(None, description="comma separated; movie must match ALL"),
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    min_rating: Optional[float] = Query(None, description="critic rating 0-10"),
    max_runtime: Optional[int] = None,
    sort: str = "popular",
    page: int = 1,
    page_size: int = Query(24, le=60),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(optional_user),
):
    ratings, watch = services.user_ratings(db, user), services.user_watchlist(db, user)
    ids = list(state.movies)
    gs = [g for g in (genres or "").split(",") if g]

    def ok(mid):
        m = state.movies[mid]
        return (
            all(g in m["genres"] for g in gs)
            and (year_min is None or m["year"] >= year_min)
            and (year_max is None or m["year"] <= year_max)
            and (min_rating is None or m["critic_rating"] >= min_rating)
            and (max_runtime is None or m["runtime"] <= max_runtime)
        )

    ids = [i for i in ids if ok(i)]
    if q and q.strip():
        ranked = services.search(q, ids)
        order = {mid: n for n, mid in enumerate(ranked)}
        ids = ranked
        if sort == "popular":
            sort = "relevance"
    else:
        order = {}
    rec = state.rec
    key = {
        "relevance": lambda i: order.get(i, 1e9),
        "popular": lambda i: -(rec.pop[rec.id2idx[i]]),
        "rating": lambda i: -state.movies[i]["critic_rating"],
        "year_desc": lambda i: -state.movies[i]["year"],
        "year_asc": lambda i: state.movies[i]["year"],
        "title": lambda i: state.movies[i]["title"].lower(),
        "runtime": lambda i: state.movies[i]["runtime"],
    }
    matches = {}
    if sort == "match" and user:
        recs = rec.recommend(ratings, services.fav_genres(user), n=len(state.movies), allowed=ids)
        matches = {s.movie_id: s for s in recs}
        ids = [s.movie_id for s in recs] + [i for i in ids if i not in matches]
    else:
        ids.sort(key=key.get(sort, key["popular"]))
    total = len(ids)
    start = (page - 1) * page_size
    items = []
    for mid in ids[start:start + page_size]:
        if mid in matches:
            items.append(services.scored_to_dict(matches[mid], ratings, watch))
        else:
            items.append(services.serialize(mid, ratings, watch, brief=True))
    return dict(total=total, page=page, page_size=page_size, pages=int(np.ceil(total / page_size)) if total else 0, items=items)


@router.get("/search/suggest")
def suggest(q: str, db: Session = Depends(get_db)):
    ids = services.search(q)[:7]
    return [dict(id=i, title=state.movies[i]["title"], year=state.movies[i]["year"],
                 poster=f"/api/posters/{i}.svg", genres=state.movies[i]["genres"][:2]) for i in ids]


@router.get("/movies/{movie_id}")
def movie_detail(movie_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(optional_user)):
    if movie_id not in state.movies:
        raise HTTPException(404, "Movie not found")
    ratings, watch = services.user_ratings(db, user), services.user_watchlist(db, user)
    extra = {}
    if user:
        rec = state.rec
        s = rec.score_user(ratings, services.fav_genres(user))
        i = rec.id2idx[movie_id]
        if not s["seen"][i]:
            h = float(s["hybrid"][i])
            reason, anchor = rec._reason(i, s, services.fav_genres(user))
            extra.update(
                match=int(round(55 + 44 * min(max(h, 0), 1))),
                reason=reason,
                predicted_rating=round(float(np.clip(s["cf_raw"][i], 0.5, 5.0)), 1) if s["n"] >= 3 else None,
                explain=dict(
                    weights={k: round(v, 3) for k, v in s["weights"].items()},
                    signals=dict(
                        collaborative=round(float(s["cf"][i]), 3), content=round(float(s["content"][i]), 3),
                        genre_affinity=round(float(s["genre"][i]), 3), popularity=round(float(s["pop"][i]), 3),
                    ),
                ),
            )
    d = services.serialize(movie_id, ratings, watch, extra=extra)
    mine = db.query(Rating).filter(Rating.user_id == user.id, Rating.movie_id == movie_id).first() if user else None
    d["user_review"] = mine.review if mine else ""
    reviews = (
        db.query(Rating, User).join(User, User.id == Rating.user_id)
        .filter(Rating.movie_id == movie_id, Rating.review != "").order_by(Rating.updated_at.desc()).limit(10).all()
    )
    d["reviews"] = [dict(username=u.username, avatar_color=u.avatar_color, rating=r.value, review=r.review,
                         date=r.updated_at.isoformat()) for r, u in reviews]
    return d


@router.get("/movies/{movie_id}/similar")
def similar(movie_id: int, n: int = 12, db: Session = Depends(get_db), user: Optional[User] = Depends(optional_user)):
    if movie_id not in state.movies:
        raise HTTPException(404)
    ratings, watch = services.user_ratings(db, user), services.user_watchlist(db, user)
    out = []
    for s in state.rec.similar(movie_id, n):
        out.append(services.serialize(s.movie_id, ratings, watch, brief=True))
    return out
