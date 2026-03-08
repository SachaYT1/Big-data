#!/usr/bin/env python3
import argparse
import os
import time

import psycopg2


Q1 = """
SELECT p.country, COUNT(*) AS total_checkins
FROM checkins c
JOIN pois p ON p.poi_id = c.poi_id
GROUP BY p.country
ORDER BY total_checkins DESC
LIMIT 10;
"""

Q2 = """
WITH stable_friendships AS (
    SELECT b.userid, b.friendid
    FROM friendship_before b
    INNER JOIN friendship_after a
        ON a.userid = b.userid AND a.friendid = b.friendid
),
friend_pois AS (
    SELECT sf.userid, c.poi_id, COUNT(*) AS friend_checkin_count
    FROM stable_friendships sf
    JOIN checkins c ON c.userid = sf.friendid
    GROUP BY sf.userid, c.poi_id
),
user_visited AS (
    SELECT DISTINCT userid, poi_id
    FROM checkins
)
SELECT fp.userid, fp.poi_id, p.category, p.country, fp.friend_checkin_count
FROM friend_pois fp
JOIN pois p ON p.poi_id = fp.poi_id
LEFT JOIN user_visited uv
    ON uv.userid = fp.userid AND uv.poi_id = fp.poi_id
WHERE uv.poi_id IS NULL
ORDER BY fp.friend_checkin_count DESC, fp.userid
LIMIT 50;
"""

Q3 = """
SELECT
    c.poi_id,
    p.category,
    p.country,
    p.latitude,
    p.longitude,
    COUNT(*) AS total_shares
FROM checkins c
JOIN pois p ON p.poi_id = c.poi_id
GROUP BY c.poi_id, p.category, p.country, p.latitude, p.longitude
ORDER BY total_shares DESC
LIMIT 20;
"""

Q4 = """
WITH classified AS (
    SELECT
        poi_id,
        CASE
            WHEN to_tsvector('english', category) @@ to_tsquery('english', 'restaurant | cafe | diner | food | pizza | burger')
                THEN 'Restaurant'
            WHEN to_tsvector('english', category) @@ to_tsquery('english', 'club | bar | pub | nightlife | lounge | disco | karaoke')
                THEN 'Club'
            WHEN to_tsvector('english', category) @@ to_tsquery('english', 'museum | gallery | art | historic')
                THEN 'Museum'
            WHEN to_tsvector('english', category) @@ to_tsquery('english', 'shop | store | market | mall | boutique')
                THEN 'Shop'
            ELSE 'Others'
        END AS custom_category
    FROM pois
)
SELECT custom_category, COUNT(*) AS venue_count
FROM classified
WHERE custom_category = %(target)s
GROUP BY custom_category;
"""


def get_conn(dbname: str):
    return psycopg2.connect(
        dbname=dbname,
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
    )


def run_benchmark(cur, label: str, sql: str, params=None, runs: int = 3):
    print(f"\n=== {label} ===")
    durations = []
    first_result = None

    for i in range(1, runs + 1):
        started = time.perf_counter()
        cur.execute(sql, params or {})
        result = cur.fetchall()
        elapsed = time.perf_counter() - started
        durations.append(elapsed)
        print(f"Run {i}: {elapsed:.4f} sec, rows={len(result)}")
        if first_result is None:
            first_result = result

    avg = sum(durations) / len(durations)
    print(f"Average: {avg:.4f} sec")
    print("Sample output (first 10 rows):")
    for row in (first_result or [])[:10]:
        print(row)
    return avg


def main():
    parser = argparse.ArgumentParser(description="Run analytical queries on Citus")
    parser.add_argument("--dbname", default="foursquaredb")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--q4-category", default="Club")
    args = parser.parse_args()

    conn = get_conn(args.dbname)
    conn.autocommit = True
    with conn.cursor() as cur:
        # Keep memory usage predictable on containerized workers.
        cur.execute("SET max_parallel_workers_per_gather = 0;")
        cur.execute("SET work_mem = '16MB';")
        avg_q1 = run_benchmark(cur, "Q1: Top 10 countries by check-ins", Q1, runs=args.runs)
        avg_q2 = run_benchmark(cur, "Q2: Stable-friend POI recommendations", Q2, runs=args.runs)
        avg_q3 = run_benchmark(cur, "Q3: Most attractive venues by location", Q3, runs=args.runs)
        avg_q4 = run_benchmark(
            cur,
            f"Q4: Number of venues in category '{args.q4_category}'",
            Q4,
            params={"target": args.q4_category},
            runs=args.runs,
        )

    print("\n=== AVERAGE RUNTIMES (seconds) ===")
    print(f"Q1\t{avg_q1:.4f}")
    print(f"Q2\t{avg_q2:.4f}")
    print(f"Q3\t{avg_q3:.4f}")
    print(f"Q4\t{avg_q4:.4f}")
    conn.close()


if __name__ == "__main__":
    main()
