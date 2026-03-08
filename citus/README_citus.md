# Citus Quick Start (3-node cluster)

## What is Citus

Citus is an extension for PostgreSQL that turns Postgres into distributed SQL:
- one **coordinator** receives SQL queries,
- multiple **worker nodes** store shards and execute work in parallel.

You still write SQL/`psycopg2` code, but tables can be distributed by a shard key.

## Why this design for the assignment

- Main fact table `checkins` is distributed by `userid` to parallelize user-centric analytics.
- `friendship_before` and `friendship_after` are also distributed by `userid` for co-location with user-based operations.
- `pois` is a reference table (replicated on workers) to make POI joins local.

## Prerequisites

- Docker Desktop installed and running
- Python venv with `psycopg2-binary`

## 1) Start cluster

```bash
cd "/Users/algavkovskii/uni/Big data/citus"
docker compose up -d
```

## 2) Register workers in Citus

```bash
docker exec -i citus_coordinator psql -U postgres -d foursquaredb < setup_cluster.sql
```
This setup uses trust auth inside the Docker network, so coordinator-to-worker connections do not require password prompts.

## 3) Run ingestion

From project root:

```bash
cd "/Users/algavkovskii/uni/Big data"
source venv/bin/activate
export PGHOST=localhost
export PGPORT=5433
export PGUSER=postgres
export PGPASSWORD=postgres

python citus/ingest_citus.py --dbname foursquaredb --skip-create-db
```

## 4) Run analytical queries (Q1-Q4)

```bash
python citus/run_queries_citus.py --dbname foursquaredb --runs 3 --q4-category Club
```

## Troubleshooting: "No space left on device" in shared memory

If queries fail with `could not resize shared memory segment ... No space left on device`:

```bash
cd "/Users/algavkovskii/uni/Big data/citus"
docker compose down
docker compose up -d --force-recreate
```

This project sets `shm_size: 1gb` per Citus container to avoid `/dev/shm` exhaustion.

## 5) Stop cluster

```bash
cd "/Users/algavkovskii/uni/Big data/citus"
docker compose down
```
