# Airflow 3 + Postgres starter

A small, honest data pipeline stack you can stand up in one step: **Apache Airflow 3.3.2** (LocalExecutor)
and **Postgres 17**, wired together with Docker Compose. It ships with a working CSV → Postgres ETL DAG
and a series of hands-on tutorials built around real production failures.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/taliff0001/airflow_postgres_etl_starter_code?quickstart=1)

## Quick start

**In the browser (nothing to install):** click the Codespaces badge above. GitHub builds a cloud machine,
runs the setup, and opens the Airflow UI on a forwarded port. First build takes a few minutes.

**On your machine** (needs [Docker Desktop](https://www.docker.com/products/docker-desktop/) running):

```bash
git clone https://github.com/taliff0001/airflow_postgres_etl_starter_code.git
cd airflow_postgres_etl_starter_code
./setup.sh
```

Then open http://localhost:8080 and sign in with `admin` / `admin`.

`setup.sh` creates your `.env` (generating the Fernet key and JWT secret), checks that the ports are free,
starts the containers, and waits until every health check passes. Run it again any time; it's safe.

| | |
|---|---|
| Stop the stack | `docker compose down` |
| Wipe everything (containers, volumes, logs) and start fresh | `./setup.sh --clean` |
| Reset the tutorial tables | `./setup.sh --reset` |
| Postgres from your laptop | `localhost:5433`, user `airflow`, password `airflow`, database `warehouse` |

## Tutorials

| # | Problem | What you build |
|---|---|---|
| [01](tutorials/01-idempotent-loads/) | A pipeline retries after a failure and duplicates half the table | An idempotent load, fixed two ways: key + `ON CONFLICT`, and staging + `MERGE` |

Each tutorial starts with a real failure someone described on LinkedIn, reproduces it on this stack, and
fixes it, with a checkpoint after every step so you know you're on track.

## What's in the stack

```
.
├── docker-compose.yml   Postgres + Airflow (init, API server, scheduler, DAG processor)
├── setup.sh             one-command setup, --reset, --clean
├── .env.example         the settings you can change (ports, login, Airflow version)
├── init-db/             SQL that Postgres runs on first start (creates the `warehouse` database)
├── dags/                your DAGs; the folder is mounted into Airflow, edits show up live
├── data/                sample CSVs for the starter ETL DAG
└── tutorials/           one folder per tutorial
```

Two databases live in the one Postgres container: `airflow` (Airflow's own metadata) and `warehouse`
(yours). DAGs reach `warehouse` through an Airflow Connection named `warehouse_db`, defined in
`docker-compose.yml`, so no DAG ever hard-codes a connection string.

### The starter DAG

`csv_to_postgres_etl` reads two CSVs from `data/`, cleans them with pandas, merges them, and writes
`merged_data` to the `warehouse` database. Trigger it from the UI, then look at the result:

```bash
docker compose exec postgres psql -U airflow -d warehouse -c "SELECT * FROM merged_data;"
```

### Airflow 3 notes

If you last used Airflow 2, three things in this stack are new: the webserver is now an **API server**
(FastAPI), the **DAG processor** is a separate required service, and tasks no longer talk to the
metadata database; they go through the API server. DAGs use the Airflow 3 Task SDK imports
(`from airflow.sdk import DAG, task`), and `schedule_interval` is now `schedule`.

## Settings

Everything adjustable is in `.env` (created from `.env.example` on first run):

| Variable | Default | |
|---|---|---|
| `AIRFLOW_PORT` | `8080` | host port for the UI |
| `POSTGRES_PORT` | `5433` | host port for Postgres (5433 so a local Postgres on 5432 doesn't collide) |
| `AIRFLOW_USER` / `AIRFLOW_PASSWORD` | `admin` / `admin` | UI login |
| `AIRFLOW_VERSION` | `3.3.2` | image tag |
| `_PIP_ADDITIONAL_REQUIREMENTS` | empty | extra packages a DAG needs |

## Troubleshooting

- **"Port 8080 is already in use."** Change `AIRFLOW_PORT` in `.env` and re-run `./setup.sh`.
- **A DAG doesn't appear.** The folder is rescanned every 10 s. Still missing after that:
  `docker compose exec airflow-dag-processor airflow dags list-import-errors`
- **Something's wedged.** `./setup.sh --clean` rebuilds from nothing.
- **Linux: files in `logs/` owned by root.** `setup.sh` sets `AIRFLOW_UID` in `.env` automatically; if you
  created `.env` by hand, add `AIRFLOW_UID=$(id -u)`.

## License

MIT
