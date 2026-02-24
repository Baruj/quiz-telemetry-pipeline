import os
from fastapi.testclient import TestClient

# Para correr local/CI sin explotar si no está seteada
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://quiz:quiz@localhost:5432/quizops",
)

# OJO: importamos desde el “root” de apps/api
from main import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
