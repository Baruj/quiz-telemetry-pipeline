```md

\# QuizOps — mini telemetry pipeline (API + Postgres + dbt + Airflow)



QuizOps es un proyecto demo de data engineering que junta en un solo repo:



\- \*\*API (FastAPI)\*\* para exponer quizzes, crear intentos (attempts) y guardar respuestas (answers).

\- \*\*Postgres\*\* como base de datos operativa.

\- \*\*dbt (Postgres adapter)\*\* para construir un modelo analítico simple (staging + marts) sobre las tablas operativas.

\- \*\*Airflow\*\* para orquestar `dbt run` → `dbt test`.

\- \*\*CI (GitHub Actions)\*\* que levanta Postgres, inicializa schema, corre tests de API y corre dbt.



La idea es tener un “pipeline de punta a punta” pequeño pero realista: ingestión (API) → persistencia (Postgres) → transformación (dbt) → orquestación (Airflow) → validación (tests + CI).



---



\## Arquitectura (qué corre y por qué)



\### 1) Operacional (API + DB)

\- La \*\*API\*\* escribe y lee desde Postgres usando SQLAlchemy y SQL (via `text()`).

\- Tablas operativas: `quizzes`, `questions`, `users`, `attempts`, `answers` (ver `scripts/init.sql`).



\### 2) Analítica (dbt)

\- dbt modela \*\*vistas\*\* (por default) en 2 capas:

&nbsp; - \*\*staging\*\*: `stg\_answers`

&nbsp; - \*\*marts\*\*: `fact\_attempt`, `fact\_answer`

\- Es deliberadamente simple: el objetivo es enseñar el flujo end-to-end y tests básicos.



\### 3) Orquestación (Airflow)

\- DAG: `quizops\_dbt\_pipeline`

\- Ejecuta secuencialmente:

&nbsp; 1. `dbt run`

&nbsp; 2. `dbt test`

\- Está configurado en modo \*\*manual\*\* (`schedule=None`) para demo rápida.



---



\## Estructura del repo



```



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

└─ test\_health.py        # smoke test del endpoint /health



````



---



\## Requisitos



\### Opción A (recomendada): Docker

\- Docker Desktop (Windows/Mac) o Docker Engine (Linux)

\- docker compose v2



\### Opción B (local sin docker, útil para debug)

\- Python 3.12

\- Postgres local

\- dbt (si vas a correr transformaciones localmente)



---



\## Arranque rápido (Docker)



Desde la raíz del repo:



```bash

docker compose -f infra/docker-compose.yml up -d --build

````



Servicios principales y puertos:



\* API: \[http://localhost:8000](http://localhost:8000)

\* Airflow UI: \[http://localhost:8080](http://localhost:8080)

\* Postgres (quizops): `localhost:5432`



> Nota: el stack incluye \*\*dos Postgres\*\*:

>

> \* `db` (quizops) para la API y dbt

> \* `airflow-db` para metadatos de Airflow



---



\## Inicializar base de datos (schema)



En CI esto se hace automáticamente, pero en local puedes correrlo así:



\### Opción 1: usando el contenedor `db` (recomendado)



```bash

docker exec -i infra-db-1 psql -U quiz -d quizops < scripts/init.sql

```



\### Opción 2: con `psql` local



```bash

psql -h localhost -U quiz -d quizops -f scripts/init.sql

```



Credenciales por defecto (dev):



\* user: `quiz`

\* password: `quiz`

\* db: `quizops`



---



\## Probar API (manual)



\### Health check



```bash

curl http://localhost:8000/health

\# {"status":"ok"}

```



\### Endpoints principales



\* `GET /quizzes`

&nbsp; Lista quizzes paginados (`limit`, `offset`).



\* `GET /quizzes/{quiz\_id}/questions`

&nbsp; Regresa preguntas para un quiz: `prompt`, `options`, `topic`, `difficulty`.



\* `POST /attempts`

&nbsp; Crea un intento para un quiz.



&nbsp; \* Payload:



&nbsp;   ```json

&nbsp;   { "quiz\_id": "<uuid>", "username": "opcional" }

&nbsp;   ```

&nbsp; \* Si `username` existe, reutiliza `user\_id`; si no existe, lo crea.



\* `POST /attempts/{attempt\_id}/answers`

&nbsp; Upsert de respuesta por `(attempt\_id, question\_id)`.



&nbsp; \* Payload:



&nbsp;   ```json

&nbsp;   { "question\_id": "<uuid>", "chosen\_index": 0 }

&nbsp;   ```



\* `POST /attempts/{attempt\_id}/submit`

&nbsp; Calcula score comparando `chosen\_index` vs `correct\_index` y marca `submitted\_at`.



> Tip: la API usa `DATABASE\_URL` (SQLAlchemy). En Docker, el `host` es el service name `db`.



---



\## Correr dbt



\### Con Docker (recomendado)



El servicio `dbt` usa la imagen `ghcr.io/dbt-labs/dbt-postgres:1.8.2` y monta el proyecto en `/dbt`.



```bash

docker compose -f infra/docker-compose.yml run --rm dbt dbt debug --profiles-dir /dbt

docker compose -f infra/docker-compose.yml run --rm dbt dbt run   --profiles-dir /dbt

docker compose -f infra/docker-compose.yml run --rm dbt dbt test  --profiles-dir /dbt

```



\### Modelos (views) que construye



\* `staging.stg\_answers`

&nbsp; Base staging de respuestas.



\* `marts.fact\_attempt`

&nbsp; “Hechos” del intento (started/submitted/score/max\_score).



\* `marts.fact\_answer`

&nbsp; Respuestas por intento/pregunta con `is\_correct` (join answers + questions).



---



\## Airflow (orquestación)



\* UI: \[http://localhost:8080](http://localhost:8080)

&nbsp; Usuario: `admin`

&nbsp; Password: `admin`



DAG disponible:



\* `quizops\_dbt\_pipeline`



El DAG corre:



1\. `dbt run`

2\. `dbt test`



Por ahora está en modo manual (`schedule=None`) para facilitar demo.



---



\## Tests (pytest)



\### En Docker/CI



En CI se setea `PYTHONPATH=apps/api` para que `from main import app` funcione con el layout del repo, y `DATABASE\_URL` apunta al Postgres service.



\### En local (sin docker)



Asegúrate de tener `DATABASE\_URL` apuntando a tu Postgres local:



```bash

pip install -r apps/api/requirements.txt

pip install -r apps/api/requirements-dev.txt

pytest -q

```



Si necesitas setear `DATABASE\_URL` en Windows (PowerShell):



```powershell

$env:DATABASE\_URL="postgresql+psycopg2://quiz:quiz@localhost:5432/quizops"

pytest -q

```



---



\## CI (GitHub Actions)



Workflow: `.github/workflows/ci.yml`



Qué valida:



1\. Levanta Postgres 16 como service

2\. Inicializa schema con `scripts/init.sql`

3\. Corre `pytest`

4\. Instala `dbt-postgres==1.8.2`

5\. Corre `dbt debug`, `dbt run`, `dbt test`



Esto asegura que el repo “se construye solo” y que dbt + API están alineados.



---



\## Variables de entorno



\### API



\* `DATABASE\_URL` (requerida)



&nbsp; \* Docker: `postgresql+psycopg2://quiz:quiz@db:5432/quizops`

&nbsp; \* Local:  `postgresql+psycopg2://quiz:quiz@localhost:5432/quizops`



\### dbt (profiles.yml)



dbt toma estos env vars (con defaults):



\* `DB\_HOST` (default: `db`)

\* `DB\_USER` (default: `quiz`)

\* `DB\_PASSWORD` (default: `quiz`)

\* `DB\_PORT` (default: `5432`)

\* `DB\_NAME` (default: `quizops`)



Schema destino dbt: `analytics` (configurado en `dbt/profiles.yml`).



---



\## Troubleshooting rápido



\*\*1) “connection refused” en API o dbt\*\*



\* Verifica que `db` esté healthy:



&nbsp; ```bash

&nbsp; docker compose -f infra/docker-compose.yml ps

&nbsp; ```

\* Revisa logs:



&nbsp; ```bash

&nbsp; docker compose -f infra/docker-compose.yml logs db --tail=80

&nbsp; docker compose -f infra/docker-compose.yml logs api --tail=80

&nbsp; ```



\*\*2) Airflow levanta pero no aparece el DAG\*\*



\* Verifica volumen de DAGs:

&nbsp; `../airflow/dags:/opt/airflow/dags`

\* Logs del scheduler:



&nbsp; ```bash

&nbsp; docker compose -f infra/docker-compose.yml logs airflow-scheduler --tail=120

&nbsp; ```



\*\*3) dbt corre pero no ves modelos\*\*



\* Asegúrate de usar el `--profiles-dir` correcto:



&nbsp; \* En docker dbt container: `--profiles-dir /dbt`

&nbsp; \* En Airflow: `--profiles-dir /opt/airflow/dbt`



---



\## Próximos pasos (ideas)



\* Seed/demo data: agregar script para insertar quizzes/questions de ejemplo.

\* dbt tests más reales (relationships, accepted\_values).

\* Métricas: tasa de acierto por quiz/topic/difficulty.

\* Endpoint de “analytics summary” consumiendo tablas marts.

\* Cambiar DAG a `@daily` y agregar `dbt source freshness`.



---



\## Licencia



Ver `LICENSE` y `LICENSE-COMMERCIAL.md`.



```

::contentReference\[oaicite:0]{index=0}

```



