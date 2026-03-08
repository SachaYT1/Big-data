# MongoDB Quick Start (3-node replica set)

## What is MongoDB

MongoDB is a document-oriented NoSQL database.  
For this assignment we use a **reference-based** design (separate collections with ids), which keeps POI data centralized and avoids large duplication in check-ins.

## 1) Start replica set containers

```bash
cd "/Users/algavkovskii/uni/Big data/mongodb"
docker compose up -d
```

## 2) Initialize replica set

```bash
docker exec -i mongo1 mongosh --quiet < init_replicaset.js
```

Check status:

```bash
docker exec -i mongo1 mongosh --quiet --eval "rs.status().members.map(m => ({name: m.name, state: m.stateStr}))"
```

You should see one `PRIMARY` and two `SECONDARY`.

Note: replica-set members are configured with Docker-internal names (`mongo1/2/3`). Host-side scripts connect via `mongodb://localhost:27020/?directConnection=true` to the primary node.

## 3) Python dependency

From project root:

```bash
cd "/Users/algavkovskii/uni/Big data"
source venv312/bin/activate
pip install pymongo
```

## 4) Ingestion

```bash
python mongodb/ingest_mongodb.py --uri "mongodb://localhost:27020/?directConnection=true" --db foursquaredb
```

## 5) Query benchmark (Q1-Q4)

```bash
python mongodb/run_queries_mongodb.py --uri "mongodb://localhost:27020/?directConnection=true" --db foursquaredb --runs 3 --q4-category Club
```

## 6) Shutdown

```bash
cd "/Users/algavkovskii/uni/Big data/mongodb"
docker compose down
```
