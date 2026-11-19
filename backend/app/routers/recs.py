"""Personalised recommendation feeds."""
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..models import User
from ..security import optional_user
from ..services import state

router = APIRouter(prefix="/api/recs", tags=["recommendations"])


def _row(title, subtitle, items, kind="poster"):
    return dict(title=title, subtitle=subtitle, items=items, kind=kind)


@router.get("/home")
def home(db: Session = Depends(get_db), user: Optional[User] = Depends(optional_user)):
    rec = state.rec
    ratings, watch = services.user_ratings(db, user), services.user_watchlist(db, user)
    favs = services.fav_genres(user)
    personal = bool(user and (ratings or favs))
    rows = []
    sc = lambda lst: [services.scored_to_dict(s, ratings, watch) for s in lst]

    top = rec.recommend(ratings, favs, n=24, exclude=watch)
    hero = top[0] if top else None
    if personal:
        rows.append(_row("Top picks for you", "Hybrid AI: collaborative + content + taste profile", sc(top[:18])))
        # because you loved X  (up to 2 anchors)
        liked = sorted([(v, k) for k, v in ratings.items() if v >= 4.5], reverse=True)[:2]
        used = set(s.movie_id for s in top[:6])
        for _, mid in liked:
            sim = [s for s in rec.similar(mid, 20) if s.movie_id not in ratings][:14]
            if sim:
                rows.append(_row(f"Because you loved {state.movies[mid]['title']}", "Item-to-item similarity",
                                 [services.serialize(s.movie_id, ratings, watch, brief=True) for s in sim]))
        # favourite genres
        gscore = {}
        for mid, v in ratings.items():
            for g in state.movies[mid]["genres"]:
                gscore[g] = gscore.get(g, 0) + (v - 3)
        for g in favs:
            gscore[g] = gscore.get(g, 0) + 2.5
        for g in [g for g, _ in sorted(gscore.items(), key=lambda x: -x[1])[:2]]:
            allowed = [i for i, m in state.movies.items() if g in m["genres"]]
            lst = rec.recommend(ratings, favs, n=14, allowed=allowed)
            rows.append(_row(f"More {g} for you", f"Your strongest genre signal", sc(lst)))

    # trending (popularity) -- everyone
    trend = rec.recommend(ratings, favs, n=16, mode="popularity")
    rows.append(_row("Trending now", "What the community is watching", sc(trend)))
    # hidden gems: high critic score, few ratings
    gems = [(state.movies[i]["critic_rating"] - 0.02 * rec.n_ratings[rec.id2idx[i]], i) for i in state.movies
            if i not in ratings and state.movies[i]["critic_rating"] >= 8.0]
    gems.sort(reverse=True)
    quiet = sorted([i for _, i in gems], key=lambda i: rec.n_ratings[rec.id2idx[i]])[:14]
    rows.append(_row("Hidden gems", "Acclaimed, but under-watched", [services.serialize(i, ratings, watch, brief=True) for i in quiet]))
    # critics
    acclaimed = sorted([i for i in state.movies if i not in ratings], key=lambda i: -state.movies[i]["critic_rating"])[:14]
    rows.append(_row("Critically acclaimed", "Highest rated of all time", [services.serialize(i, ratings, watch, brief=True) for i in acclaimed]))
    # decade/mood rows for explorers
    for title, sub, pred in [
        ("Mind-bending sci-fi", "Reality is optional", lambda m: "Sci-Fi" in m["genres"] and any(k in m["keywords"] for k in ("twist", "mind bending", "time travel", "simulation", "identity", "reality", "multiverse", "memory loss"))),
        ("Edge-of-your-seat thrillers", "Don't blink", lambda m: "Thriller" in m["genres"]),
        ("Feel-good favourites", "Comfort cinema", lambda m: ("Comedy" in m["genres"] or "Family" in m["genres"]) and m["critic_rating"] >= 7.8),
    ]:
        ids = [i for i, m in state.movies.items() if pred(m) and i not in ratings]
        ids.sort(key=lambda i: -state.movies[i]["critic_rating"])
        if len(ids) >= 5:
            rows.append(_row(title, sub, [services.serialize(i, ratings, watch, brief=True) for i in ids[:14]]))

    if not personal:  # no taste signal yet -> a "match %" would be meaningless
        for r in rows:
            for it in r["items"]:
                it.pop("match", None)
    hero_d = None
    if hero:
        hero_d = services.scored_to_dict(hero, ratings, watch)
        hero_d.update(cast=state.movies[hero.movie_id]["cast"], director=state.movies[hero.movie_id]["director"])
        if not personal:
            hero_d.pop("match", None)
            hero_d["reason"] = "Trending with the community"
    return dict(personalized=personal, hero=hero_d, rows=rows)


@router.get("/for-you")
def for_you(
    n: int = Query(30, le=100),
    mode: str = Query("hybrid", pattern="^(hybrid|cf|content|popularity)$"),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(optional_user),
):
    ratings, watch = services.user_ratings(db, user), services.user_watchlist(db, user)
    recs = state.rec.recommend(ratings, services.fav_genres(user), n=n, mode=mode)
    return [services.scored_to_dict(s, ratings, watch) for s in recs]


@router.get("/onboarding")
def onboarding_picks(db: Session = Depends(get_db)):
    """A diverse set of well-known films for the cold-start taste quiz (greedy max-diversity over genres)."""
    rec = state.rec
    pool = sorted(state.movies, key=lambda i: -(rec.pop[rec.id2idx[i]]))[:70]
    chosen, covered = [], {}
    for _ in range(18):
        best = max((i for i in pool if i not in chosen),
                   key=lambda i: sum(1.0 / (1 + covered.get(g, 0)) for g in state.movies[i]["genres"]) + 0.3 * rec.pop[rec.id2idx[i]])
        chosen.append(best)
        for g in state.movies[best]["genres"]:
            covered[g] = covered.get(g, 0) + 1
    return [services.serialize(i, brief=True) for i in chosen]
