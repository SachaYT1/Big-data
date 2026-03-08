#!/usr/bin/env python3
import argparse
import time

from pymongo import MongoClient


def run_benchmark(label: str, fn, runs: int = 3):
    print(f"\n=== {label} ===")
    durations = []
    first_rows = None
    for i in range(1, runs + 1):
        started = time.perf_counter()
        rows = fn()
        elapsed = time.perf_counter() - started
        durations.append(elapsed)
        print(f"Run {i}: {elapsed:.4f} sec, rows={len(rows)}")
        if first_rows is None:
            first_rows = rows
    avg = sum(durations) / len(durations)
    print(f"Average: {avg:.4f} sec")
    print("Sample output (first 10 rows):")
    for row in (first_rows or [])[:10]:
        print(row)
    return avg


def main():
    parser = argparse.ArgumentParser(description="Run analytical queries on MongoDB")
    parser.add_argument(
        "--uri",
        default="mongodb://localhost:27020/?directConnection=true",
    )
    parser.add_argument("--db", default="foursquaredb")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--q4-category", default="Club")
    args = parser.parse_args()

    client = MongoClient(args.uri)
    db = client[args.db]

    def q1():
        pipeline = [
            {"$lookup": {"from": "pois", "localField": "poi_id", "foreignField": "_id", "as": "poi"}},
            {"$unwind": "$poi"},
            {"$group": {"_id": "$poi.country", "total_checkins": {"$sum": 1}}},
            {"$sort": {"total_checkins": -1}},
            {"$limit": 10},
            {"$project": {"_id": 0, "country": "$_id", "total_checkins": 1}},
        ]
        return list(db.checkins.aggregate(pipeline, allowDiskUse=True))

    def q2():
        pipeline = [
            {
                "$lookup": {
                    "from": "checkins",
                    "localField": "friendid",
                    "foreignField": "userid",
                    "as": "friend_checkins",
                }
            },
            {"$unwind": "$friend_checkins"},
            {
                "$group": {
                    "_id": {"userid": "$userid", "poi_id": "$friend_checkins.poi_id"},
                    "friend_checkin_count": {"$sum": 1},
                }
            },
            {
                "$lookup": {
                    "from": "checkins",
                    "let": {"u": "$_id.userid", "p": "$_id.poi_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$and": [{"$eq": ["$userid", "$$u"]}, {"$eq": ["$poi_id", "$$p"]}]}}},
                        {"$limit": 1},
                    ],
                    "as": "already_visited",
                }
            },
            {"$match": {"already_visited": {"$eq": []}}},
            {"$lookup": {"from": "pois", "localField": "_id.poi_id", "foreignField": "_id", "as": "poi"}},
            {"$unwind": "$poi"},
            {
                "$project": {
                    "_id": 0,
                    "userid": "$_id.userid",
                    "poi_id": "$_id.poi_id",
                    "category": "$poi.category",
                    "country": "$poi.country",
                    "friend_checkin_count": 1,
                }
            },
            {"$sort": {"friend_checkin_count": -1, "userid": 1}},
            {"$limit": 50},
        ]
        return list(db.stable_friendships.aggregate(pipeline, allowDiskUse=True))

    def q3():
        pipeline = [
            {"$group": {"_id": "$poi_id", "total_shares": {"$sum": 1}}},
            {"$sort": {"total_shares": -1}},
            {"$limit": 20},
            {"$lookup": {"from": "pois", "localField": "_id", "foreignField": "_id", "as": "poi"}},
            {"$unwind": "$poi"},
            {
                "$project": {
                    "_id": 0,
                    "poi_id": "$_id",
                    "category": "$poi.category",
                    "country": "$poi.country",
                    "latitude": "$poi.latitude",
                    "longitude": "$poi.longitude",
                    "total_shares": 1,
                }
            },
        ]
        return list(db.checkins.aggregate(pipeline, allowDiskUse=True))

    def q4():
        q4_map = {
            "Restaurant": "restaurant cafe diner food pizza burger",
            "Club": "club bar pub nightlife lounge disco karaoke",
            "Museum": "museum gallery art historic",
            "Shop": "shop store market mall boutique",
            "Others": "",
        }
        target = args.q4_category
        if target in q4_map and q4_map[target]:
            count = db.pois.count_documents({"$text": {"$search": q4_map[target]}})
        elif target == "Others":
            known = "restaurant cafe diner food pizza burger club bar pub nightlife lounge disco karaoke museum gallery art historic shop store market mall boutique"
            count = db.pois.count_documents({"$text": {"$search": known}})
            count = db.pois.count_documents({}) - count
        else:
            count = 0
        return [{"custom_category": target, "venue_count": count}]

    avg_q1 = run_benchmark("Q1: Top 10 countries by check-ins", q1, runs=args.runs)
    avg_q2 = run_benchmark("Q2: Stable-friend POI recommendations", q2, runs=args.runs)
    avg_q3 = run_benchmark("Q3: Most attractive venues by location", q3, runs=args.runs)
    avg_q4 = run_benchmark(f"Q4: Number of venues in category '{args.q4_category}'", q4, runs=args.runs)

    print("\n=== AVERAGE RUNTIMES (seconds) ===")
    print(f"Q1\t{avg_q1:.4f}")
    print(f"Q2\t{avg_q2:.4f}")
    print(f"Q3\t{avg_q3:.4f}")
    print(f"Q4\t{avg_q4:.4f}")

    client.close()


if __name__ == "__main__":
    main()
