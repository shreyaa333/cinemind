"""
CineMind recommendation engine.

Three signals are combined into one hybrid score:

  1. CONTENT-BASED   TF-IDF over genres / keywords / people / plot overview.
                     A per-user taste profile is the rating-weighted average of the
                     TF-IDF vectors of films the user liked; candidates are ranked by
                     cosine similarity to that profile.

  2. COLLABORATIVE   Matrix factorisation trained with Alternating Least Squares (ALS):
                         r_ui ~ mu + b_u + b_i + p_u . q_i
                     Item parameters are learned offline. A user vector is obtained
                     with a closed-form ridge "fold-in", so a brand-new rating changes
                     recommendations instantly with no retraining.

  3. POPULARITY /    Bayesian-damped rating + log popularity + catalogue critic score,
     GENRE PRIOR     plus a genre prior from onboarding picks. These solve the cold
                     start problem for new users.

Blend weights adapt to how much the user has rated (confidence alpha), so the system
smoothly moves from "popular + your favourite genres" to "deeply personalised".
"""
from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from scipy import sparse


def _minmax(x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Min-max scale to [0,1], computed over the masked (candidate) entries only."""
    x = np.asarray(x, dtype=float)
    ref = x[mask] if mask is not None and mask.any() else x
    lo, hi = ref.min(), ref.max()
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


@dataclass
class Scored:
    movie_id: int
    score: float
    match: int
    reason: str
    anchor_id: Optional[int]
    predicted_rating: Optional[float]


class Recommender:
    def __init__(self, k: int = 16, lam: float = 8.0, iters: int = 15, seed: int = 7):
        self.k, self.lam, self.iters, self.seed = k, lam, iters, seed
        self.fitted = False

    # ------------------------------------------------------------------ fit
    def fit(self, movies: pd.DataFrame, ratings: pd.DataFrame) -> "Recommender":
        self.movies = movies.sort_values("movie_id").reset_index(drop=True)
        self.movie_ids = self.movies["movie_id"].to_numpy()
        self.id2idx = {int(m): i for i, m in enumerate(self.movie_ids)}
        self.n_items = len(self.movies)
        self.all_genres = sorted({g for gs in self.movies["genres"] for g in gs.split("|")})

        self._fit_content()
        self._fit_cf(ratings)
        self._fit_popularity(ratings)
        self.fitted = True
        return self

    # --- content ---------------------------------------------------------
    def _fit_content(self):
        m = self.movies
        genres = m["genres"].str.replace("|", " ", regex=False).str.replace("-", "", regex=False)
        keywords = m["keywords"].apply(lambda s: " ".join(k.strip().replace(" ", "_") + " " + k.strip() for k in s.split("|")))
        people = (m["director"] + "|" + m["director"] + "|" + m["cast"]).apply(
            lambda s: " ".join(p.strip().replace(" ", "_").replace(".", "") for p in s.split("|"))
        )
        overview = m["overview"]
        blocks = [
            (TfidfVectorizer(token_pattern=r"[A-Za-z0-9_]+", lowercase=True), genres, 1.00),
            (TfidfVectorizer(token_pattern=r"[A-Za-z0-9_]+", lowercase=True), keywords, 0.80),
            (TfidfVectorizer(token_pattern=r"[A-Za-z0-9_]+", lowercase=True), people, 0.55),
            (TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True), overview, 0.45),
        ]
        mats = []
        for vec, col, w in blocks:
            X = vec.fit_transform(col)
            mats.append(normalize(X) * w)
        self.X_content = normalize(sparse.hstack(mats).tocsr())
        self.content_sim = (self.X_content @ self.X_content.T).toarray()
        np.fill_diagonal(self.content_sim, 0.0)

        # genre membership matrix (n_items x n_genres) for genre priors / explanations
        g_idx = {g: j for j, g in enumerate(self.all_genres)}
        G = np.zeros((self.n_items, len(self.all_genres)))
        for i, gs in enumerate(m["genres"]):
            for g in gs.split("|"):
                G[i, g_idx[g]] = 1.0
        self.G = G
        self.g_idx = g_idx

    # --- collaborative filtering (ALS with biases) ---------------------------
    def _fit_cf(self, ratings: pd.DataFrame):
        r = ratings[ratings["movie_id"].isin(self.id2idx)].copy()
        users = np.sort(r["user_id"].unique())
        uidx = {int(u): i for i, u in enumerate(users)}
        ui = r["user_id"].map(uidx).to_numpy()
        ii = r["movie_id"].map(self.id2idx).to_numpy()
        rr = r["rating"].to_numpy(dtype=float)

        n_u, n_i, k = len(users), self.n_items, self.k
        self.mu = float(rr.mean())

        # group by user and by item
        def group(keys, n):
            order = np.argsort(keys, kind="stable")
            bounds = np.searchsorted(keys[order], np.arange(n + 1))
            return order, bounds

        u_order, u_b = group(ui, n_u)
        i_order, i_b = group(ii, n_i)

        rng = np.random.default_rng(self.seed)
        Q = rng.normal(0, 0.1, (n_i, k))
        P = np.zeros((n_u, k))
        bu = np.zeros(n_u)
        bi = np.zeros(n_i)

        reg_u = np.diag([self.lam * 0.5] + [self.lam] * k)
        eye = np.eye(k + 1)

        for _ in range(self.iters):
            # --- update users given items
            for u in range(n_u):
                sl = u_order[u_b[u]:u_b[u + 1]]
                if len(sl) == 0:
                    continue
                items, y = ii[sl], rr[sl]
                F = np.hstack([np.ones((len(items), 1)), Q[items]])
                t = y - self.mu - bi[items]
                w = np.linalg.solve(F.T @ F + reg_u, F.T @ t)
                bu[u], P[u] = w[0], w[1:]
            # --- update items given users
            for i in range(n_i):
                sl = i_order[i_b[i]:i_b[i + 1]]
                if len(sl) == 0:
                    continue
                us, y = ui[sl], rr[sl]
                F = np.hstack([np.ones((len(us), 1)), P[us]])
                t = y - self.mu - bu[us]
                w = np.linalg.solve(F.T @ F + reg_u, F.T @ t)
                bi[i], Q[i] = w[0], w[1:]

        self.Q, self.bi, self.P_train, self.bu_train = Q, bi, P, bu
        self.reg_u = reg_u
        self.train_users = users
        self.train_rmse = float(np.sqrt(np.mean((self._predict_pairs(P, bu, ui, ii) - rr) ** 2)))
        # item-item similarity in latent space
        Qn = normalize(Q)
        self.cf_sim = Qn @ Qn.T
        np.fill_diagonal(self.cf_sim, 0.0)

    def _predict_pairs(self, P, bu, ui, ii):
        return self.mu + bu[ui] + self.bi[ii] + np.einsum("nk,nk->n", P[ui], self.Q[ii])

    # --- popularity ----------------------------------------------------------
    def _fit_popularity(self, ratings: pd.DataFrame):
        g = ratings.groupby("movie_id")["rating"].agg(["mean", "count"])
        mean_r = np.full(self.n_items, ratings["rating"].mean())
        cnt = np.zeros(self.n_items)
        for mid, row in g.iterrows():
            if int(mid) in self.id2idx:
                mean_r[self.id2idx[int(mid)]] = row["mean"]
                cnt[self.id2idx[int(mid)]] = row["count"]
        C, m = ratings["rating"].mean(), 8.0
        bayes = (cnt / (cnt + m)) * mean_r + (m / (cnt + m)) * C
        critic = self.movies["avg_rating"].to_numpy() / 2.0
        self.n_ratings = cnt
        self.bayes = bayes
        self.pop = 0.5 * _minmax(critic) + 0.3 * _minmax(bayes) + 0.2 * _minmax(np.log1p(cnt))

    # ------------------------------------------------------------ user model
    def fold_in(self, idx: np.ndarray, r: np.ndarray):
        """Closed-form user vector from the user's ratings given fixed item factors."""
        F = np.hstack([np.ones((len(idx), 1)), self.Q[idx]])
        t = r - self.mu - self.bi[idx]
        w = np.linalg.solve(F.T @ F + self.reg_u, F.T @ t)
        return float(w[0]), w[1:]

    def predict_all(self, idx: np.ndarray, r: np.ndarray, with_factors: bool = True) -> np.ndarray:
        if len(idx) == 0:
            return self.mu + self.bi
        bu, p = self.fold_in(idx, r)
        out = self.mu + bu + self.bi
        if with_factors:
            out = out + self.Q @ p
        return out

    def content_scores(self, idx: np.ndarray, r: np.ndarray) -> np.ndarray:
        """Cosine similarity of every film to the user's taste profile."""
        if len(idx) == 0:
            return np.zeros(self.n_items)
        centred = r - r.mean() if r.std() > 1e-9 else r - 2.5
        w = np.where(centred > 0, centred, 0.35 * centred)  # dislikes push away, more gently
        if np.all(w <= 0):
            w = r - 2.0
        prof = sparse.csr_matrix(w) @ self.X_content[idx]
        prof = normalize(prof)
        return np.asarray((self.X_content @ prof.T).todense()).ravel()

    def genre_prior(self, fav_genres: Sequence[str], idx: np.ndarray, r: np.ndarray) -> np.ndarray:
        """Genre affinity from onboarding picks and from what the user rated highly."""
        vec = np.zeros(len(self.all_genres))
        for g in fav_genres or []:
            if g in self.g_idx:
                vec[self.g_idx[g]] += 1.0
        if len(idx):
            w = np.clip(r - 3.0, -1.5, 2.0)
            vec = vec + (w[:, None] * self.G[idx]).sum(0) / max(len(idx), 1) * 3
        if np.abs(vec).max() < 1e-9:
            return np.zeros(self.n_items)
        vec = vec / np.abs(vec).max()
        s = self.G @ vec / np.maximum(self.G.sum(1), 1)
        return s

    # --------------------------------------------------------- recommendation
    def score_user(self, ratings: Dict[int, float], fav_genres: Sequence[str] = ()) -> dict:
        idx = np.array([self.id2idx[m] for m in ratings if m in self.id2idx], dtype=int)
        r = np.array([ratings[m] for m in ratings if m in self.id2idx], dtype=float)
        n = len(idx)
        seen = np.zeros(self.n_items, dtype=bool)
        seen[idx] = True
        cand = ~seen

        cf_raw = self.predict_all(idx, r) if n >= 3 else self.mu + self.bi
        cf = _minmax(cf_raw, cand)
        ct = _minmax(self.content_scores(idx, r), cand) if n else np.zeros(self.n_items)
        gp = _minmax(self.genre_prior(fav_genres, idx, r), cand)
        pop = _minmax(self.pop, cand)

        alpha = 1 - math.exp(-n / 10.0)
        w_cf = 0.50 * alpha
        w_ct = 0.25 * alpha
        w_gp = 0.35 * (1 - alpha) + 0.05 if (len(fav_genres) or n) else 0.0
        w_pop = 1.0 - w_cf - w_ct - w_gp
        hybrid = w_cf * cf + w_ct * ct + w_gp * gp + w_pop * pop
        return dict(idx=idx, r=r, seen=seen, cand=cand, cf=cf, cf_raw=cf_raw, content=ct, genre=gp, pop=pop,
                    hybrid=hybrid, weights=dict(cf=w_cf, content=w_ct, genre=w_gp, popularity=w_pop), n=n)

    def _reason(self, i: int, s: dict, fav_genres: Sequence[str]):
        idx, r = s["idx"], s["r"]
        if len(idx):
            liked = r >= 4.0
            if liked.any():
                sims = self.content_sim[i, idx] * 0.6 + self.cf_sim[i, idx] * 0.4
                sims = np.where(liked, sims, -1)
                j = int(np.argmax(sims))
                if sims[j] > 0.22:
                    mid = int(self.movie_ids[idx[j]])
                    return f"Because you loved {self.movies.loc[idx[j], 'title']}", mid
            # dominant shared genres
            if liked.any():
                gscore = (self.G[idx[liked]] * (r[liked] - 3)[:, None]).sum(0)
                top = [self.all_genres[j] for j in np.argsort(-gscore)[:3] if gscore[j] > 0]
                mine = [g for g in self.movies.loc[i, "genres"].split("|") if g in top]
                if mine:
                    return f"Matches your taste for {' & '.join(mine[:2])}", None
        mine = [g for g in self.movies.loc[i, "genres"].split("|") if g in (fav_genres or [])]
        if mine:
            return f"Picked because you like {mine[0]}", None
        if self.movies.loc[i, "avg_rating"] >= 8.4:
            return "Critically acclaimed", None
        return "Popular with viewers like you", None

    def recommend(
        self,
        ratings: Dict[int, float],
        fav_genres: Sequence[str] = (),
        n: int = 20,
        allowed: Optional[Iterable[int]] = None,
        exclude: Iterable[int] = (),
        mode: str = "hybrid",
    ) -> List[Scored]:
        s = self.score_user(ratings, fav_genres)
        score = dict(hybrid=s["hybrid"], cf=s["cf"], content=s["content"], popularity=s["pop"]).get(mode, s["hybrid"])
        mask = s["cand"].copy()
        for e in exclude:
            if e in self.id2idx:
                mask[self.id2idx[e]] = False
        if allowed is not None:
            allow = np.zeros(self.n_items, dtype=bool)
            for a in allowed:
                if a in self.id2idx:
                    allow[self.id2idx[a]] = True
            mask &= allow
        cand_idx = np.where(mask)[0]
        order = cand_idx[np.argsort(-score[cand_idx])][:n]
        out = []
        for i in order:
            reason, anchor = self._reason(int(i), s, fav_genres)
            hs = float(s["hybrid"][i])
            out.append(
                Scored(
                    movie_id=int(self.movie_ids[i]),
                    score=hs,
                    match=int(round(55 + 44 * min(max(hs, 0), 1))),
                    reason=reason,
                    anchor_id=anchor,
                    predicted_rating=float(np.clip(s["cf_raw"][i], 0.5, 5.0)) if s["n"] >= 3 else None,
                )
            )
        return out

    def similar(self, movie_id: int, n: int = 12) -> List[Scored]:
        i = self.id2idx[movie_id]
        sim = 0.65 * self.content_sim[i] + 0.35 * np.clip(self.cf_sim[i], 0, None)
        order = np.argsort(-sim)[:n]
        mx = max(sim[order[0]], 1e-9)
        return [
            Scored(int(self.movie_ids[j]), float(sim[j]), int(round(100 * sim[j] / mx * 0.99)), "Similar", movie_id, None)
            for j in order
        ]

    def taste_vector(self, ratings: Dict[int, float]) -> Dict[str, float]:
        """Genre affinity in [0,1] for radar charts on the profile page."""
        if not ratings:
            return {}
        agg = {g: [] for g in self.all_genres}
        for mid, rv in ratings.items():
            if mid in self.id2idx:
                for g in self.movies.loc[self.id2idx[mid], "genres"].split("|"):
                    agg[g].append(rv)
        return {g: round(float(np.mean(v)) / 5.0, 3) for g, v in agg.items() if v}

    # -------------------------------------------------------------------- io
    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "Recommender":
        with open(path, "rb") as f:
            return pickle.load(f)
