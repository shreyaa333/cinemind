import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
MODEL_DIR = os.getenv("CINEMIND_MODEL_DIR", os.path.join(ROOT, "models"))
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(ROOT, 'cinemind.db')}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production-please-0123456789")
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "168"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
