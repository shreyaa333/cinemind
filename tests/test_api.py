"""End-to-end API tests. Run:  pytest -q   (uses a throw-away SQLite DB)"""
import os
import tempfile

import shutil

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
# tests (incl. the admin retrain endpoint) work on a throw-away copy so the shipped model is never touched
_models = os.path.join(_tmp, "models")
shutil.copytree(os.path.join(os.path.dirname(__file__), "..", "models"), _models)
os.environ["CINEMIND_MODEL_DIR"] = _models

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def auth(c, email="t1@example.com"):
    r = c.post("/api/auth/register", json={"email": email, "username": "Tester", "password": "secret12"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_health(client):
    j = client.get("/api/health").json()
    assert j["status"] == "ok" and j["movies"] > 100 and j["model_loaded"]


def test_auth_flow(client):
    h = auth(client)
    assert client.post("/api/auth/register", json={"email": "t1@example.com", "username": "xx", "password": "secret12"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "t1@example.com", "password": "bad"}).status_code == 401
    ok = client.post("/api/auth/login", json={"email": "t1@example.com", "password": "secret12"})
    assert ok.status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["email"] == "t1@example.com"
    assert client.get("/api/auth/me").status_code == 401


def test_search_and_filters(client):
    r = client.get("/api/movies", params={"q": "inceptoin"}).json()  # typo tolerant
    assert r["items"][0]["title"] == "Inception"
    r = client.get("/api/movies", params={"q": "nolan"}).json()
    assert r["total"] >= 6
    r = client.get("/api/movies", params={"genres": "Horror,Thriller", "year_min": 2000}).json()
    assert r["total"] > 0 and all({"Horror", "Thriller"} <= set(m["genres"]) and m["year"] >= 2000 for m in r["items"])
    assert client.get("/api/search/suggest", params={"q": "dark kni"}).json()[0]["title"] == "The Dark Knight"
    assert client.get("/api/posters/1.svg").headers["content-type"].startswith("image/svg")


def test_rating_watchlist_and_recs_change(client):
    h = auth(client, "t2@example.com")
    cold = client.get("/api/recs/for-you", headers=h).json()
    assert len(cold) > 10
    # rate a bunch of animation/family films highly and horror low -> recs must shift
    movies = client.get("/api/movies", params={"genres": "Animation", "page_size": 12}).json()["items"]
    for m in movies[:8]:
        assert client.put(f"/api/ratings/{m['id']}", json={"value": 5}, headers=h).status_code == 200
    horror = client.get("/api/movies", params={"genres": "Horror", "page_size": 5}).json()["items"]
    for m in horror[:4]:
        client.put(f"/api/ratings/{m['id']}", json={"value": 1}, headers=h)
    warm = client.get("/api/recs/for-you", headers=h, params={"n": 10}).json()
    anim_share = sum("Animation" in m["genres"] or "Family" in m["genres"] for m in warm) / len(warm)
    assert anim_share >= 0.6, anim_share
    assert all(m["user_rating"] is None for m in warm)  # never recommends already-rated films
    # watchlist
    mid = warm[0]["id"]
    assert client.post(f"/api/watchlist/{mid}", headers=h).json()["in_watchlist"] is True
    assert any(m["id"] == mid for m in client.get("/api/watchlist", headers=h).json())
    assert client.post(f"/api/watchlist/{mid}", headers=h).json()["in_watchlist"] is False
    # detail has explanation + similar
    d = client.get(f"/api/movies/{mid}", headers=h).json()
    assert d["match"] >= 55 and "explain" in d
    assert len(client.get(f"/api/movies/{mid}/similar").json()) == 12


def test_home_and_profile(client):
    h = auth(client, "t3@example.com")
    anon = client.get("/api/recs/home").json()
    assert anon["personalized"] is False and len(anon["rows"]) >= 3
    picks = client.get("/api/recs/onboarding").json()
    assert len(picks) == 18
    r = client.post("/api/profile/onboarding", headers=h, json={"fav_genres": ["Sci-Fi", "Thriller"], "ratings": {picks[0]["id"]: 5, picks[1]["id"]: 4}})
    assert r.json()["onboarded"] is True
    home = client.get("/api/recs/home", headers=h).json()
    assert home["personalized"] is True and home["hero"] and home["rows"][0]["title"] == "Top picks for you"
    s = client.get("/api/profile/stats", headers=h).json()
    assert s["rated"] == 2 and s["persona"]
    assert client.put("/api/profile", headers=h, json={"bio": "hi", "avatar_color": "#112233"}).json()["bio"] == "hi"
    m = client.get("/api/system/metrics").json()
    assert m["ranking"]["hybrid"]["ndcg_at_10"] > m["ranking"]["popularity"]["ndcg_at_10"]


def test_demo_user_and_admin_retrain(client):
    r = client.post("/api/auth/login", json={"email": "demo@cinemind.dev", "password": "demo1234"})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    top = client.get("/api/recs/for-you", headers=h, params={"n": 8}).json()
    assert any("Sci-Fi" in m["genres"] for m in top[:5])
    assert client.post("/api/system/retrain", headers=h).status_code == 200
