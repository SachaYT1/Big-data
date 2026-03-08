#!/usr/bin/env python3
import argparse
import time

from cassandra.cluster import Cluster


Q1 = "SELECT country, total_checkins FROM q1_top_countries WHERE bucket = 1 LIMIT 10;"
Q2 = (
    "SELECT userid, poi_id, category, country, score "
    "FROM q2_recommendations_global WHERE bucket = 1 LIMIT 50;"
)
Q3 = (
    "SELECT poi_id, category, country, latitude, longitude, total_shares "
    "FROM q3_attractive_venues_global WHERE bucket = 1 LIMIT 20;"
)
Q4 = "SELECT custom_category, venue_count FROM q4_custom_category_counts WHERE custom_category = %s;"


def run_benchmark(session, label: str, query: str, params=None, runs: int = 3):
    print(f"\n=== {label} ===")
    durations = []
    first_rows = None
    for i in range(1, runs + 1):
        started = time.perf_counter()
        result = session.execute(query, params or [])
        rows = list(result)
        elapsed = time.perf_counter() - started
        durations.append(elapsed)
        print(f"Run {i}: {elapsed:.4f} sec, rows={len(rows)}")
        if first_rows is None:
            first_rows = rows
    avg = sum(durations) / len(durations)
    print(f"Average: {avg:.4f} sec")
    print("Sample output (first 10 rows):")
    for row in (first_rows or [])[:10]:
        print(tuple(row))
    return avg


def main():
    parser = argparse.ArgumentParser(description="Run analytical queries on ScyllaDB")
    parser.add_argument("--hosts", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9042)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--q4-category", default="Club")
    args = parser.parse_args()

    hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]
    cluster = Cluster(contact_points=hosts, port=args.port)
    session = cluster.connect("foursquaredb")

    avg_q1 = run_benchmark(session, "Q1: Top 10 countries by check-ins", Q1, runs=args.runs)
    avg_q2 = run_benchmark(session, "Q2: Stable-friend POI recommendations", Q2, runs=args.runs)
    avg_q3 = run_benchmark(session, "Q3: Most attractive venues by location", Q3, runs=args.runs)
    avg_q4 = run_benchmark(
        session,
        f"Q4: Number of venues in category '{args.q4_category}'",
        Q4,
        params=[args.q4_category],
        runs=args.runs,
    )

    print("\n=== AVERAGE RUNTIMES (seconds) ===")
    print(f"Q1\t{avg_q1:.4f}")
    print(f"Q2\t{avg_q2:.4f}")
    print(f"Q3\t{avg_q3:.4f}")
    print(f"Q4\t{avg_q4:.4f}")

    cluster.shutdown()


if __name__ == "__main__":
    main()
