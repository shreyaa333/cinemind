"""Shared in-memory state: movie catalogue cache, loaded recommender, helpers."""
import os
import threading
from difflib import SequenceMatcher
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from .config import DATA_DIR, MODEL_DIR
from .ml.recommender import Recommender
from .models import Movie, Rating, User, WatchlistItem


class State:
    rec: Optional[Recommender] = None
    movies: Dict[int, dict] = {}
    lock = threading.Lock()


state = State()


def load_catalogue(db: Session):
    state.movies = {}
    for m in db.query(Movie).all():
        state.movies[m.id] = dict(
            id=m.id, title=m.title, year=m.year, genres=m.genres.split("|"), director=m.director,
            cast=m.cast.split("|"), runtime=m.runtime, keywords=m.keywords.split("|"),
            overview=m.overview, critic_rating=m.critic_rating,
        )


def load_recommender():
    path = os.path.join(MODEL_DIR, "recommender.pkl")
    if not os.path.exists(path):
        from .ml import train
        train.main()
    state.rec = Recommender.load(path)


def user_ratings(db: Session, user: Optional[User]) -> Dict[int, float]:
    if not user:
        return {}
    return {r.movie_id: r.value for r in db.query(Rating).filter(Rating.user_id == user.id)}


def user_watchlist(db: Session, user: Optional[User]) -> set:
    if not user:
        return set()
    return {w.movie_id for w in db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id)}


def fav_genres(user: Optional[User]) -> List[str]:
    return [g for g in (user.fav_genres.split(",") if user and user.fav_genres else []) if g]


def community(mid: int):
    rec = state.rec
    i = rec.id2idx.get(mid)
    if i is None:
        return None, 0
    return round(float(rec.bayes[i]), 2), int(rec.n_ratings[i])


def serialize(mid: int, ratings=None, watch=None, extra: Optional[dict] = None, brief: bool = False) -> dict:
    m = state.movies[mid]
    avg, cnt = community(mid)
    d = dict(
        id=mid, title=m["title"], year=m["year"], genres=m["genres"], runtime=m["runtime"],
        critic_rating=m["critic_rating"], community_rating=avg, rating_count=cnt,
        poster=f"/api/posters/{mid}.svg", backdrop=f"/api/posters/{mid}/backdrop.svg",
        user_rating=(ratings or {}).get(mid), in_watchlist=mid in (watch or set()),
        director=m["director"],
    )
    if not brief:
        d.update(overview=m["overview"], cast=m["cast"], keywords=m["keywords"])
    else:
        d["overview"] = m["overview"]
    if extra:
        d.update(extra)
    return d


def scored_to_dict(s, ratings, watch) -> dict:
    anchor = state.movies[s.anchor_id]["title"] if s.anchor_id and s.anchor_id in state.movies else None
    return serialize(
        s.movie_id, ratings, watch,
        extra=dict(match=s.match, reason=s.reason, anchor=anchor,
                   predicted_rating=round(s.predicted_rating, 1) if s.predicted_rating else None),
        brief=True,
    )


# ------------------------------------------------------------------ search
def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def search_score(q: str, mid: int) -> float:
    m = state.movies[mid]
    q = q.lower().strip()
    toks = [t for t in q.replace(":", " ").split() if t]
    if not toks:
        return 0.0
    title = m["title"].lower()
    people = " ".join([m["director"]] + m["cast"]).lower()
    kw = " ".join(m["keywords"]).lower()
    genres = " ".join(m["genres"]).lower()
    over = m["overview"].lower()
    s = 0.0
    if q == title:
        s += 12
    elif title.startswith(q):
        s += 8
    elif q in title:
        s += 6
    for t in toks:
        tw = title.split()
        if any(w.startswith(t) for w in tw):
            s += 2.5
        if t in people:
            s += 2.0
        if t in kw:
            s += 1.6
        if t in genres:
            s += 1.2
        if t in over:
            s += 0.5
    # typo tolerance on title words
    if s == 0:
        best = max([_sim(q, title)] + [_sim(t, w) for t in toks for w in title.split()])
        if best > 0.72:
            s += best * 3
    return s


def search(q: str, pool: Optional[List[int]] = None) -> List[int]:
    ids = pool if pool is not None else list(state.movies)
    scored = [(search_score(q, i), i) for i in ids]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: (-x[0], -state.movies[x[1]]["critic_rating"]))
    return [i for _, i in scored]


def retrain(db: Session):
    """Retrain the recommender on the bundled dataset + every real user rating in the DB."""
    movies = pd.read_csv(os.path.join(DATA_DIR, "movies.csv"))
    base = pd.read_csv(os.path.join(DATA_DIR, "ratings.csv"))
    live = pd.DataFrame(
        [(100000 + r.user_id, r.movie_id, r.value) for r in db.query(Rating).all()],
        columns=["user_id", "movie_id", "rating"],
    )
    allr = pd.concat([base, live], ignore_index=True)
    best = Recommender(k=8, lam=6.0, iters=12).fit(movies, allr)
    best.save(os.path.join(MODEL_DIR, "recommender.pkl"))
    with state.lock:
        state.rec = best
    return dict(ratings_used=len(allr), live_ratings=len(live), train_rmse=round(best.train_rmse, 4))
