#!/usr/bin/env python3
import argparse
import csv
import time
from pathlib import Path

from pymongo import ASCENDING, MongoClient, TEXT


ROOT = Path(__file__).resolve().parents[1]


def batched_insert(collection, rows, batch_size=20000):
    if not rows:
        return
    for i in range(0, len(rows), batch_size):
        collection.insert_many(rows[i : i + batch_size], ordered=False)


def load_users(db, batch_size: int) -> float:
    started = time.perf_counter()
    rows = []
    with (ROOT / "my_users.csv").open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({"_id": int(r["userid"])})
            if len(rows) >= batch_size:
                db.users.insert_many(rows, ordered=False)
                rows.clear()
    batched_insert(db.users, rows, batch_size)
    return time.perf_counter() - started


def load_pois(db, batch_size: int) -> float:
    started = time.perf_counter()
    rows = []
    with (ROOT / "my_POIs.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            poi_id, lat_s, lon_s, category, country = line.rstrip("\n").split("\t", 4)
            rows.append(
                {
                    "_id": poi_id,
                    "latitude": float(lat_s),
                    "longitude": float(lon_s),
                    "category": category,
                    "country": country,
                }
            )
            if len(rows) >= batch_size:
                db.pois.insert_many(rows, ordered=False)
                rows.clear()
    batched_insert(db.pois, rows, batch_size)
    return time.perf_counter() - started


def load_checkins(db, batch_size: int) -> float:
    started = time.perf_counter()
    rows = []
    with (ROOT / "my_checkins_anonymized.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            uid_s, poi_id, checkin_time, tz_s = line.rstrip("\n").split("\t", 3)
            rows.append(
                {
                    "userid": int(uid_s),
                    "poi_id": poi_id,
                    "checkin_time": checkin_time,
                    "tz_offset_minutes": int(tz_s),
                }
            )
            if len(rows) >= batch_size:
                db.checkins.insert_many(rows, ordered=False)
                rows.clear()
    batched_insert(db.checkins, rows, batch_size)
    return time.perf_counter() - started


def load_friendships(db, batch_size: int) -> tuple[float, set[tuple[int, int]], set[tuple[int, int]]]:
    started = time.perf_counter()
    before_pairs: set[tuple[int, int]] = set()
    after_pairs: set[tuple[int, int]] = set()

    rows = []
    with (ROOT / "my_frienship_before.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            uid_s, fid_s = line.rstrip("\n").split("\t")
            pair = (int(uid_s), int(fid_s))
            before_pairs.add(pair)
            rows.append({"userid": pair[0], "friendid": pair[1]})
            if len(rows) >= batch_size:
                db.friendship_before.insert_many(rows, ordered=False)
                rows.clear()
    batched_insert(db.friendship_before, rows, batch_size)

    rows = []
    with (ROOT / "my_frienship_after.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            uid_s, fid_s = line.rstrip("\n").split("\t")
            pair = (int(uid_s), int(fid_s))
            after_pairs.add(pair)
            rows.append({"userid": pair[0], "friendid": pair[1]})
            if len(rows) >= batch_size:
                db.friendship_after.insert_many(rows, ordered=False)
                rows.clear()
    batched_insert(db.friendship_after, rows, batch_size)
    return time.perf_counter() - started, before_pairs, after_pairs


def load_stable_friendships(db, stable_pairs: set[tuple[int, int]], batch_size: int) -> float:
    started = time.perf_counter()
    rows = [{"userid": u, "friendid": f} for (u, f) in stable_pairs]
    batched_insert(db.stable_friendships, rows, batch_size)
    return time.perf_counter() - started


def create_indexes(db) -> float:
    started = time.perf_counter()
    db.users.create_index([("_id", ASCENDING)], unique=True)
    db.pois.create_index([("_id", ASCENDING)], unique=True)
    db.pois.create_index([("country", ASCENDING)])
    db.pois.create_index([("category", TEXT)])

    db.checkins.create_index([("userid", ASCENDING)])
    db.checkins.create_index([("poi_id", ASCENDING)])
    db.checkins.create_index([("userid", ASCENDING), ("poi_id", ASCENDING)])

    db.friendship_before.create_index([("userid", ASCENDING), ("friendid", ASCENDING)], unique=True)
    db.friendship_after.create_index([("userid", ASCENDING), ("friendid", ASCENDING)], unique=True)
    db.stable_friendships.create_index([("userid", ASCENDING), ("friendid", ASCENDING)], unique=True)
    db.friendship_before.create_index([("friendid", ASCENDING)])
    db.friendship_after.create_index([("friendid", ASCENDING)])
    return time.perf_counter() - started


def main():
    parser = argparse.ArgumentParser(description="Ingest Foursquare slice into MongoDB")
    parser.add_argument(
        "--uri",
        default="mongodb://localhost:27020,localhost:27021,localhost:27022/?replicaSet=rs0",
    )
    parser.add_argument("--db", default="foursquaredb")
    parser.add_argument("--batch-size", type=int, default=20000)
    args = parser.parse_args()

    client = MongoClient(args.uri)
    db = client[args.db]

    # Reset database for repeatable ingestion benchmark
    client.drop_database(args.db)
    db = client[args.db]

    timings = {}
    timings["users"] = load_users(db, args.batch_size)
    timings["pois"] = load_pois(db, args.batch_size)
    timings["checkins"] = load_checkins(db, args.batch_size)
    friendships_time, before_pairs, after_pairs = load_friendships(db, args.batch_size)
    timings["friendships"] = friendships_time
    timings["stable_friendships"] = load_stable_friendships(db, before_pairs.intersection(after_pairs), args.batch_size)
    timings["indexes"] = create_indexes(db)

    total = sum(timings.values())
    print("\nMongoDB ingestion timing (seconds):")
    for k in ["users", "pois", "checkins", "friendships", "stable_friendships", "indexes"]:
        print(f"  {k:18s} {timings[k]:10.2f}")
    print(f"  {'TOTAL':18s} {total:10.2f}")

    client.close()


if __name__ == "__main__":
    main()
