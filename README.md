# QuizOps — mini telemetry pipeline (API + Postgres + dbt + Airflow)

QuizOps es un proyecto demo de data engineering que junta en un solo repo:

- **API (FastAPI)** para exponer quizzes, crear intentos (*attempts*) y guardar respuestas (*answers*).
- **Postgres** como base de datos operativa.
- **dbt (Postgres adapter)** para construir un modelo analítico simple (staging + marts) sobre las tablas operativas.
- **Airflow** para orquestar `dbt run` → `dbt test`.
- **CI (GitHub Actions)** que levanta Postgres, inicializa el *schema*, corre tests de API y corre dbt.

La idea es tener un “pipeline de punta a punta” pequeño pero realista: ingestión (API) → persistencia (Postgres) → transformación (dbt) → orquestación (Airflow) → validación (tests + CI).

---

## Arquitectura (qué corre y por qué)

### 1) Operacional (API + DB)
- La **API** escribe y lee desde Postgres usando **SQLAlchemy** y SQL (vía `text()`).
- Tablas operativas: `quizzes`, `questions`, `users`, `attempts`, `answers` (ver `scripts/init.sql`).

### 2) Analítica (dbt)
- dbt modela **vistas** (por default) en 2 capas:
  - **staging**: `stg_answers`
  - **marts**: `fact_attempt`, `fact_answer`
- Es deliberadamente simple: el objetivo es enseñar el flujo end-to-end y tests básicos.

### 3) Orquestación (Airflow)
- DAG: `quizops_dbt_pipeline`
- Ejecuta secuencialmente:
  1. `dbt run`
  2. `dbt test`
- Está configurado en modo **manual** (`schedule=None`) para demo rápida.

---

## Estructura del repo

```text
.
├─ .github/
│  └─ workflows/ci.yml      # CI: pytest + dbt sobre Postgres service
├─ apps/
│  └─ api/                  # FastAPI app (main.py, db.py, Dockerfile)
├─ airflow/
│  └─ dags/                 # DAG que dispara dbt run/test
├─ data/                    # (reservado) data local / artefactos (ignorado en git en parte)
├─ dbt/                     # dbt project (models + profiles.yml)
├─ infra/
│  ├─ docker-compose.yml    # stack local (db, api, dbt, airflow)
│  ├─ airflow/              # Dockerfile para Airflow + dbt
│  └─ db/                   # Dockerfile de Postgres (quizops)
├─ scripts/
│  └─ init.sql              # schema inicial (tablas + índices)
└─ tests/
   └─ test_health.py        # smoke test del endpoint /health

---

## Requisitos

### Opción A (recomendada): Docker
- Docker Desktop (Windows/Mac) o Docker Engine (Linux)
- Docker Compose v2

### Opción B (local sin Docker, útil para debug)
- Python 3.12
- Postgres local
- dbt (si vas a correr transformaciones localmente)

---

## Arranque rápido (Docker)

Desde la raíz del repo:

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

Servicios principales y puertos:

- API: http://localhost:8000
- Airflow UI: http://localhost:8080
- Postgres (quizops): `localhost:5432`

> **Nota:** el stack incluye **dos Postgres**:
>
> - `db` (quizops) para la API y dbt
> - `airflow-db` para metadatos de Airflow

---

## Inicializar base de datos (schema)

En CI esto se hace automáticamente, pero en local puedes correrlo así:

### Opción 1: usando el contenedor `db` (recomendado)

```bash
docker exec -i infra-db-1 psql -U quiz -d quizops < scripts/init.sql
```

### Opción 2: con `psql` local

```bash
psql -h localhost -U quiz -d quizops -f scripts/init.sql
```

Credenciales por defecto (dev):

* user: `quiz`
* password: `quiz`
* db: `quizops`

---

## Probar API (manual)

### Health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Endpoints principales

* `GET /quizzes`
  Lista quizzes paginados (`limit`, `offset`).

* `GET /quizzes/{quiz_id}/questions`
  Regresa preguntas para un quiz: `prompt`, `options`, `topic`, `difficulty`.

* `POST /attempts`
  Crea un intento para un quiz.

  * Payload:

    ```json
    { "quiz_id": "<uuid>", "username": "opcional" }
    ```
  * Si `username` existe, reutiliza `user_id`; si no existe, lo crea.

* `POST /attempts/{attempt_id}/answers`
  Upsert de respuesta por `(attempt_id, question_id)`.

  * Payload:

    ```json
    { "question_id": "<uuid>", "chosen_index": 0 }
    ```

* `POST /attempts/{attempt_id}/submit`
  Calcula score comparando `chosen_index` vs `correct_index` y marca `submitted_at`.

> Tip: la API usa `DATABASE_URL` (SQLAlchemy). En Docker, el `host` es el service name `db`.

---

## Correr dbt

### Con Docker (recomendado)

El servicio `dbt` usa la imagen `ghcr.io/dbt-labs/dbt-postgres:1.8.2` y monta el proyecto en `/dbt`.

```bash
docker compose -f infra/docker-compose.yml run --rm dbt dbt debug --profiles-dir /dbt
docker compose -f infra/docker-compose.yml run --rm dbt dbt run   --profiles-dir /dbt
docker compose -f infra/docker-compose.yml run --rm dbt dbt test  --profiles-dir /dbt
```

### Modelos (views) que construye

* `staging.stg_answers`
  Base staging de respuestas.

* `marts.fact_attempt`
  “Hechos” del intento (started/submitted/score/max_score).

* `marts.fact_answer`
  Respuestas por intento/pregunta con `is_correct` (join answers + questions).

---

## Airflow (orquestación)

* UI: [http://localhost:8080](http://localhost:8080)
  Usuario: `admin`
  Password: `admin`

DAG disponible:

* `quizops_dbt_pipeline`

El DAG corre:

1. `dbt run`
2. `dbt test`

Por ahora está en modo manual (`schedule=None`) para facilitar demo.

---

## Tests (pytest)

### En Docker/CI

En CI se setea `PYTHONPATH=apps/api` para que `from main import app` funcione con el layout del repo, y `DATABASE_URL` apunta al Postgres service.

### En local (sin docker)

Asegúrate de tener `DATABASE_URL` apuntando a tu Postgres local:

```bash
pip install -r apps/api/requirements.txt
pip install -r apps/api/requirements-dev.txt
pytest -q
```

Si necesitas setear `DATABASE_URL` en Windows (PowerShell):

```powershell
$env:DATABASE_URL="postgresql+psycopg2://quiz:quiz@localhost:5432/quizops"
pytest -q
```

---

## CI (GitHub Actions)

Workflow: `.github/workflows/ci.yml`

Qué valida:

1. Levanta Postgres 16 como service
2. Inicializa schema con `scripts/init.sql`
3. Corre `pytest`
4. Instala `dbt-postgres==1.8.2`
5. Corre `dbt debug`, `dbt run`, `dbt test`

Esto asegura que el repo “se construye solo” y que dbt + API están alineados.

---

## Variables de entorno

### API

* `DATABASE_URL` (requerida)

  * Docker: `postgresql+psycopg2://quiz:quiz@db:5432/quizops`
  * Local:  `postgresql+psycopg2://quiz:quiz@localhost:5432/quizops`

### dbt (profiles.yml)

dbt toma estos env vars (con defaults):

* `DB_HOST` (default: `db`)
* `DB_USER` (default: `quiz`)
* `DB_PASSWORD` (default: `quiz`)
* `DB_PORT` (default: `5432`)
* `DB_NAME` (default: `quizops`)

Schema destino dbt: `analytics` (configurado en `dbt/profiles.yml`).

---

## Troubleshooting rápido

**1) “connection refused” en API o dbt**

* Verifica que `db` esté healthy:

  ```bash
  docker compose -f infra/docker-compose.yml ps
  ```
* Revisa logs:

  ```bash
  docker compose -f infra/docker-compose.yml logs db --tail=80
  docker compose -f infra/docker-compose.yml logs api --tail=80
  ```

**2) Airflow levanta pero no aparece el DAG**

* Verifica volumen de DAGs:
  `../airflow/dags:/opt/airflow/dags`
* Logs del scheduler:

  ```bash
  docker compose -f infra/docker-compose.yml logs airflow-scheduler --tail=120
  ```

**3) dbt corre pero no ves modelos**

* Asegúrate de usar el `--profiles-dir` correcto:

  * En docker dbt container: `--profiles-dir /dbt`
  * En Airflow: `--profiles-dir /opt/airflow/dbt`

---

## Próximos pasos (ideas)

* Seed/demo data: agregar script para insertar quizzes/questions de ejemplo.
* dbt tests más reales (relationships, accepted_values).
* Métricas: tasa de acierto por quiz/topic/difficulty.
* Endpoint de “analytics summary” consumiendo tablas marts.
* Cambiar DAG a `@daily` y agregar `dbt source freshness`.

---

## Licencia

Ver `LICENSE` y `LICENSE-COMMERCIAL.md`.
