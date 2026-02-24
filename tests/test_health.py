import os
from fastapi.testclient import TestClient

# En CI ya viene seteada; esto sólo ayuda si corres local sin env
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://quiz:quiz@localhost:5432/quizops",
)

# Importa como en Docker (main.py vive en apps/api)
from main import app

def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"