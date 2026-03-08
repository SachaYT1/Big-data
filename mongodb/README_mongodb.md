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

Note: this project configures replica-set members as `localhost:27020/27021/27022` so host-side Python clients can resolve member addresses.

## 3) Python dependency

From project root:

```bash
cd "/Users/algavkovskii/uni/Big data"
source venv312/bin/activate
pip install pymongo
```

## 4) Ingestion

```bash
python mongodb/ingest_mongodb.py --uri "mongodb://localhost:27020,localhost:27021,localhost:27022/?replicaSet=rs0" --db foursquaredb
```

## 5) Query benchmark (Q1-Q4)

```bash
python mongodb/run_queries_mongodb.py --uri "mongodb://localhost:27020,localhost:27021,localhost:27022/?replicaSet=rs0" --db foursquaredb --runs 3 --q4-category Club
```

## 6) Shutdown

```bash
cd "/Users/algavkovskii/uni/Big data/mongodb"
docker compose down
```
