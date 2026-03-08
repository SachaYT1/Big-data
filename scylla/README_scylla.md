# ScyllaDB Quick Start (3-node cluster)

## What is ScyllaDB

ScyllaDB is a high-performance, Cassandra-compatible distributed NoSQL database (wide-column / column-family model).  
It is optimized for partition-based reads/writes and query-driven denormalized schemas.

## Cluster setup (3 nodes)

```bash
cd "/Users/algavkovskii/uni/Big data/scylla"
docker compose up -d
```

Wait for nodes to initialize:

```bash
docker exec -it scylla1 nodetool status
```

You should see `UN` status for all 3 nodes.

If startup fails with AIO or `broadcast_rpc_address` errors, recreate the cluster:

```bash
docker compose down -v
docker compose up -d --force-recreate
```

If you still see `Could not setup Async I/O`, restart Docker Desktop and make sure no other heavy containerized databases are running, then rerun the same recreate commands.

## Python setup

From project root:

```bash
cd "/Users/algavkovskii/uni/Big data"
source venv/bin/activate
pip install cassandra-driver
```

## Ingestion

```bash
python scylla/ingest_scylla.py --hosts 127.0.0.1 --port 9042
```

This script:
- creates keyspace/tables from `scylla/schema_scylla.cql`,
- loads users, POIs, checkins, friendships,
- builds query-serving tables for Q1-Q4,
- prints total ingestion time.

## Query benchmark (Q1-Q4)

```bash
python scylla/run_queries_scylla.py --hosts 127.0.0.1 --port 9042 --runs 3 --q4-category Club
```

## Notes

- Scylla is query-driven; the schema intentionally keeps extra denormalized tables for analytics.
- Q4 category mapping is precomputed during ingestion (`custom_category`) and then queried by category count.

## Shutdown

```bash
cd "/Users/algavkovskii/uni/Big data/scylla"
docker compose down
```
