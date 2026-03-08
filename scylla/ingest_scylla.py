#!/usr/bin/env python3
import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = Path(__file__).with_name("schema_scylla.cql")


def custom_category(category: str) -> str:
    c = (category or "").lower()
    if any(k in c for k in ["restaurant", "cafe", "diner", "pizza", "burger", "food"]):
        return "Restaurant"
    if any(k in c for k in ["club", "bar", "pub", "nightlife", "lounge", "disco", "karaoke"]):
        return "Club"
    if any(k in c for k in ["museum", "gallery", "art", "historic"]):
        return "Museum"
    if any(k in c for k in ["shop", "store", "market", "mall", "boutique"]):
        return "Shop"
    return "Others"


def apply_schema(session) -> None:
    raw = SCHEMA_FILE.read_text(encoding="utf-8")
    for stmt in [s.strip() for s in raw.split(";") if s.strip()]:
        session.execute(stmt + ";")


def batch_insert(session, query: str, rows: list[tuple], concurrency: int = 128):
    if not rows:
        return
    prepared = session.prepare(query)
    execute_concurrent_with_args(session, prepared, rows, concurrency=concurrency, raise_on_first_error=True)


def main():
    parser = argparse.ArgumentParser(description="Ingest Foursquare slice into ScyllaDB")
    parser.add_argument("--hosts", default="127.0.0.1", help="Comma-separated Scylla hosts")
    parser.add_argument("--port", type=int, default=9042)
    parser.add_argument("--batch-size", type=int, default=5000)
    args = parser.parse_args()

    hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]
    cluster = Cluster(contact_points=hosts, port=args.port)
    session = cluster.connect()

    print("Applying schema...")
    apply_schema(session)
    session.set_keyspace("foursquaredb")

    # Clean query-serving tables for repeatable benchmarking.
    for table in [
        "q1_top_countries",
        "q2_recommendations_global",
        "q3_attractive_venues_global",
        "q4_custom_category_counts",
        "stable_friendship_by_user",
        "users_by_id",
        "pois_by_id",
        "checkins_by_user",
        "checkins_by_poi",
        "friendship_before_by_user",
        "friendship_after_by_user",
    ]:
        session.execute(f"TRUNCATE {table};")

    timings = {}

    # 1) users
    t0 = time.perf_counter()
    users_set: set[int] = set()
    users_rows = []
    with (ROOT / "my_users.csv").open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            uid = int(r["userid"])
            users_set.add(uid)
            users_rows.append((uid,))
            if len(users_rows) >= args.batch_size:
                batch_insert(session, "INSERT INTO users_by_id (userid) VALUES (?);", users_rows)
                users_rows.clear()
    batch_insert(session, "INSERT INTO users_by_id (userid) VALUES (?);", users_rows)
    timings["users"] = time.perf_counter() - t0

    # 2) friendships + stable set
    t0 = time.perf_counter()
    before_pairs: set[tuple[int, int]] = set()
    before_rows = []
    with (ROOT / "my_frienship_before.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            uid_s, fid_s = line.rstrip("\n").split("\t")
            uid, fid = int(uid_s), int(fid_s)
            before_pairs.add((uid, fid))
            before_rows.append((uid, fid))
            if len(before_rows) >= args.batch_size:
                batch_insert(
                    session,
                    "INSERT INTO friendship_before_by_user (userid, friendid) VALUES (?, ?);",
                    before_rows,
                )
                before_rows.clear()
    batch_insert(session, "INSERT INTO friendship_before_by_user (userid, friendid) VALUES (?, ?);", before_rows)

    after_pairs: set[tuple[int, int]] = set()
    after_rows = []
    with (ROOT / "my_frienship_after.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            uid_s, fid_s = line.rstrip("\n").split("\t")
            uid, fid = int(uid_s), int(fid_s)
            after_pairs.add((uid, fid))
            after_rows.append((uid, fid))
            if len(after_rows) >= args.batch_size:
                batch_insert(
                    session,
                    "INSERT INTO friendship_after_by_user (userid, friendid) VALUES (?, ?);",
                    after_rows,
                )
                after_rows.clear()
    batch_insert(session, "INSERT INTO friendship_after_by_user (userid, friendid) VALUES (?, ?);", after_rows)

    stable_pairs = before_pairs.intersection(after_pairs)
    stable_rows = [(u, f) for (u, f) in stable_pairs]
    batch_insert(
        session,
        "INSERT INTO stable_friendship_by_user (userid, friendid) VALUES (?, ?);",
        stable_rows,
    )
    timings["friendships"] = time.perf_counter() - t0

    # 3) POIs + category aggregation
    t0 = time.perf_counter()
    poi_map: dict[str, tuple[str, str, float, float]] = {}
    q4_counts = defaultdict(int)
    poi_rows = []
    with (ROOT / "my_POIs.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            poi_id, lat_s, lon_s, category, country = line.rstrip("\n").split("\t", 4)
            lat = float(lat_s)
            lon = float(lon_s)
            ccat = custom_category(category)
            poi_map[poi_id] = (country, category, lat, lon)
            q4_counts[ccat] += 1
            poi_rows.append((poi_id, lat, lon, category, country, ccat))
            if len(poi_rows) >= args.batch_size:
                batch_insert(
                    session,
                    "INSERT INTO pois_by_id (poi_id, latitude, longitude, category, country, custom_category) "
                    "VALUES (?, ?, ?, ?, ?, ?);",
                    poi_rows,
                )
                poi_rows.clear()
    batch_insert(
        session,
        "INSERT INTO pois_by_id (poi_id, latitude, longitude, category, country, custom_category) VALUES (?, ?, ?, ?, ?, ?);",
        poi_rows,
    )
    timings["pois"] = time.perf_counter() - t0

    # 4) checkins + derived analytics maps
    t0 = time.perf_counter()
    q1_country_counts = defaultdict(int)
    q3_poi_counts = defaultdict(int)

    friend_to_targets = defaultdict(set)
    target_users = set()
    for uid, fid in stable_pairs:
        friend_to_targets[fid].add(uid)
        target_users.add(uid)

    user_visited = defaultdict(set)
    q2_scores = defaultdict(lambda: defaultdict(int))

    by_user_rows = []
    by_poi_rows = []
    with (ROOT / "my_checkins_anonymized.tsv").open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            uid_s, poi_id, checkin_time, tz_s = line.rstrip("\n").split("\t", 3)
            uid = int(uid_s)
            tz = int(tz_s)

            by_user_rows.append((uid, checkin_time, poi_id, tz))
            by_poi_rows.append((poi_id, checkin_time, uid, tz))

            meta = poi_map.get(poi_id)
            if meta:
                q1_country_counts[meta[0]] += 1
            q3_poi_counts[poi_id] += 1

            if uid in target_users:
                user_visited[uid].add(poi_id)
            if uid in friend_to_targets:
                for target in friend_to_targets[uid]:
                    q2_scores[target][poi_id] += 1

            if len(by_user_rows) >= args.batch_size:
                batch_insert(
                    session,
                    "INSERT INTO checkins_by_user (userid, checkin_time, poi_id, tz_offset_minutes) "
                    "VALUES (?, ?, ?, ?);",
                    by_user_rows,
                )
                by_user_rows.clear()
            if len(by_poi_rows) >= args.batch_size:
                batch_insert(
                    session,
                    "INSERT INTO checkins_by_poi (poi_id, checkin_time, userid, tz_offset_minutes) "
                    "VALUES (?, ?, ?, ?);",
                    by_poi_rows,
                )
                by_poi_rows.clear()

    batch_insert(
        session,
        "INSERT INTO checkins_by_user (userid, checkin_time, poi_id, tz_offset_minutes) VALUES (?, ?, ?, ?);",
        by_user_rows,
    )
    batch_insert(
        session,
        "INSERT INTO checkins_by_poi (poi_id, checkin_time, userid, tz_offset_minutes) VALUES (?, ?, ?, ?);",
        by_poi_rows,
    )
    timings["checkins"] = time.perf_counter() - t0

    # 5) Fill Q1 ranking
    t0 = time.perf_counter()
    q1_rows = [(1, cnt, country) for country, cnt in q1_country_counts.items()]
    batch_insert(
        session,
        "INSERT INTO q1_top_countries (bucket, total_checkins, country) VALUES (?, ?, ?);",
        q1_rows,
    )
    timings["q1_table"] = time.perf_counter() - t0

    # 6) Fill Q3 ranking
    t0 = time.perf_counter()
    q3_rows = []
    for poi_id, total in q3_poi_counts.items():
        country, category, lat, lon = poi_map.get(poi_id, ("NA", "Unknown", 0.0, 0.0))
        q3_rows.append((1, total, poi_id, category, country, lat, lon))
    batch_insert(
        session,
        "INSERT INTO q3_attractive_venues_global "
        "(bucket, total_shares, poi_id, category, country, latitude, longitude) "
        "VALUES (?, ?, ?, ?, ?, ?, ?);",
        q3_rows,
    )
    timings["q3_table"] = time.perf_counter() - t0

    # 7) Fill Q2 ranking (top 20 per user after excluding already visited POIs)
    t0 = time.perf_counter()
    q2_rows = []
    for uid, score_map in q2_scores.items():
        visited = user_visited.get(uid, set())
        filtered = [(poi, s) for poi, s in score_map.items() if poi not in visited]
        filtered.sort(key=lambda x: x[1], reverse=True)
        for poi_id, score in filtered[:20]:
            country, category, _, _ = poi_map.get(poi_id, ("NA", "Unknown", 0.0, 0.0))
            q2_rows.append((1, score, uid, poi_id, category, country))
    batch_insert(
        session,
        "INSERT INTO q2_recommendations_global (bucket, score, userid, poi_id, category, country) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        q2_rows,
    )
    timings["q2_table"] = time.perf_counter() - t0

    # 8) Fill Q4 counts
    t0 = time.perf_counter()
    q4_rows = [(cat, cnt) for cat, cnt in q4_counts.items()]
    batch_insert(
        session,
        "INSERT INTO q4_custom_category_counts (custom_category, venue_count) VALUES (?, ?);",
        q4_rows,
    )
    timings["q4_table"] = time.perf_counter() - t0

    total = sum(timings.values())
    print("\nScylla ingestion timing (seconds):")
    for k in [
        "users",
        "friendships",
        "pois",
        "checkins",
        "q1_table",
        "q2_table",
        "q3_table",
        "q4_table",
    ]:
        print(f"  {k:18s} {timings[k]:10.2f}")
    print(f"  {'TOTAL':18s} {total:10.2f}")

    cluster.shutdown()


if __name__ == "__main__":
    main()
