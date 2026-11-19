"""
Train + evaluate the CineMind recommender.

    python -m app.ml.train

Steps
  1. Hyper-parameter search (latent factors k x regularisation lambda) on a validation split.
  2. Hold-out evaluation (80/20 per-user split):
       - Rating prediction: RMSE / MAE vs. baselines
       - Top-N ranking:     Precision@10, Recall@10, NDCG@10, HitRate@10, Coverage
       - Methods compared:  Random, Popularity, Content-only, CF-only, Hybrid
  3. Refit on ALL ratings, save the model to models/recommender.pkl and metrics to models/metrics.json.
"""
import json
import os
import time

import numpy as np
import pandas as pd

from .recommender import Recommender

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
MODELS = os.getenv("CINEMIND_MODEL_DIR", os.path.join(ROOT, "models"))
os.makedirs(MODELS, exist_ok=True)


def split(ratings: pd.DataFrame, frac: float, seed: int):
    rng = np.random.default_rng(seed)
    test_idx = []
    for _, g in ratings.groupby("user_id"):
        if len(g) < 6:
            continue
        n_test = max(1, int(len(g) * frac))
        test_idx.extend(rng.choice(g.index.to_numpy(), n_test, replace=False))
    test = ratings.loc[test_idx]
    return ratings.drop(test.index), test


def user_dict(df: pd.DataFrame):
    return {u: dict(zip(g["movie_id"], g["rating"])) for u, g in df.groupby("user_id")}


def rmse_mae(model: Recommender, train: pd.DataFrame, test: pd.DataFrame):
    tr, te = user_dict(train), user_dict(test)
    out = {"global_mean": [], "item_mean": [], "bias_only": [], "als": []}
    truth = []
    item_mean = train.groupby("movie_id")["rating"].agg(["sum", "count"])
    mu = train["rating"].mean()
    for u, tdict in te.items():
        hist = tr.get(u, {})
        idx = np.array([model.id2idx[m] for m in hist if m in model.id2idx], dtype=int)
        r = np.array([hist[m] for m in hist if m in model.id2idx], dtype=float)
        full = model.predict_all(idx, r, with_factors=True)
        bias = model.predict_all(idx, r, with_factors=False)
        for m, rv in tdict.items():
            truth.append(rv)
            out["global_mean"].append(mu)
            if m in item_mean.index:
                s, c = item_mean.loc[m]
                out["item_mean"].append((s + 5 * mu) / (c + 5))
            else:
                out["item_mean"].append(mu)
            out["bias_only"].append(float(np.clip(bias[model.id2idx[m]], 0.5, 5)))
            out["als"].append(float(np.clip(full[model.id2idx[m]], 0.5, 5)))
    truth = np.array(truth)
    res = {}
    for k, v in out.items():
        v = np.array(v)
        res[k] = dict(rmse=float(np.sqrt(np.mean((v - truth) ** 2))), mae=float(np.mean(np.abs(v - truth))))
    return res


def ranking_metrics(model: Recommender, train: pd.DataFrame, test: pd.DataFrame, K=10, seed=0):
    tr, te = user_dict(train), user_dict(test)
    rng = np.random.default_rng(seed)
    methods = ["random", "popularity", "content", "cf", "hybrid"]
    acc = {m: dict(p=[], r=[], ndcg=[], hit=[], recs=set()) for m in methods}
    disc = 1.0 / np.log2(np.arange(2, K + 2))
    for u, tdict in te.items():
        relevant = {m for m, rv in tdict.items() if rv >= 4.0}
        if not relevant:
            continue
        hist = tr.get(u, {})
        s = model.score_user(hist)
        cand = np.where(s["cand"])[0]
        scores = {
            "random": rng.random(model.n_items),
            "popularity": s["pop"],
            "content": s["content"],
            "cf": s["cf"],
            "hybrid": s["hybrid"],
        }
        for name, sc in scores.items():
            top = cand[np.argsort(-sc[cand])][:K]
            ids = [int(model.movie_ids[i]) for i in top]
            hits = np.array([1.0 if i in relevant else 0.0 for i in ids])
            idcg = disc[: min(len(relevant), K)].sum()
            a = acc[name]
            a["p"].append(hits.sum() / K)
            a["r"].append(hits.sum() / len(relevant))
            a["ndcg"].append(float((hits * disc).sum() / idcg))
            a["hit"].append(float(hits.sum() > 0))
            a["recs"].update(ids)
    res = {}
    for name, a in acc.items():
        res[name] = dict(
            precision_at_10=float(np.mean(a["p"])),
            recall_at_10=float(np.mean(a["r"])),
            ndcg_at_10=float(np.mean(a["ndcg"])),
            hit_rate_at_10=float(np.mean(a["hit"])),
            coverage=len(a["recs"]) / model.n_items,
            users_evaluated=len(a["p"]),
        )
    return res


def main():
    t0 = time.time()
    movies = pd.read_csv(os.path.join(DATA, "movies.csv"))
    ratings = pd.read_csv(os.path.join(DATA, "ratings.csv"))
    print(f"Loaded {len(movies)} movies, {len(ratings)} ratings, {ratings.user_id.nunique()} users")

    # ---- 1. hyper-parameter search ------------------------------------------------
    train_all, test = split(ratings, 0.2, seed=1)
    train, val = split(train_all, 0.125, seed=2)
    grid = []
    for k in [4, 8, 16, 24]:
        for lam in [4.0, 8.0, 14.0]:
            m = Recommender(k=k, lam=lam, iters=12).fit(movies, train)
            res = rmse_mae(m, train, val)["als"]
            grid.append(dict(k=k, lam=lam, val_rmse=res["rmse"]))
            print(f"  k={k:<3} lam={lam:<5} val RMSE={res['rmse']:.4f}")
    best = min(grid, key=lambda g: g["val_rmse"])
    print("Best:", best)

    # ---- 2. hold-out evaluation -----------------------------------------------------
    model = Recommender(k=best["k"], lam=best["lam"], iters=15).fit(movies, train_all)
    rating_metrics = rmse_mae(model, train_all, test)
    rank = ranking_metrics(model, train_all, test)
    print("\nRating prediction (lower is better)")
    for k, v in rating_metrics.items():
        print(f"  {k:<12} RMSE={v['rmse']:.4f}  MAE={v['mae']:.4f}")
    print("\nTop-10 ranking (higher is better)")
    for k, v in rank.items():
        print(f"  {k:<11} P@10={v['precision_at_10']:.3f} R@10={v['recall_at_10']:.3f} "
              f"NDCG@10={v['ndcg_at_10']:.3f} Hit@10={v['hit_rate_at_10']:.3f} Cov={v['coverage']:.2f}")

    # ---- 3. final fit on all data ----------------------------------------------------
    final = Recommender(k=best["k"], lam=best["lam"], iters=15).fit(movies, ratings)
    final.save(os.path.join(MODELS, "recommender.pkl"))
    metrics = dict(
        dataset=dict(movies=len(movies), ratings=len(ratings), users=int(ratings.user_id.nunique()),
                     density=len(ratings) / (ratings.user_id.nunique() * len(movies))),
        best_params=best,
        grid=grid,
        rating_prediction=rating_metrics,
        ranking=rank,
        train_rmse=final.train_rmse,
        trained_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    with open(os.path.join(MODELS, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved model + metrics to {MODELS}  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
