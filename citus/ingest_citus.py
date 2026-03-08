#!/usr/bin/env python3
import argparse
import os
import time
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = Path(__file__).with_name("schema_citus.sql")


def get_conn(dbname: str):
    return psycopg2.connect(
        dbname=dbname,
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "1234"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
    )


def ensure_database(dbname: str) -> None:
    conn = get_conn("postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
        if cur.fetchone() is None:
            print(f"Creating database '{dbname}'...")
            cur.execute(f'CREATE DATABASE "{dbname}";')
        else:
            print(f"Database '{dbname}' already exists.")
    conn.close()


def copy_file(cur, sql: str, path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        cur.copy_expert(sql, f)


def build_schema(conn) -> None:
    raw_sql = SCHEMA_SQL.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in raw_sql.split(";") if stmt.strip()]
    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt + ";")
    conn.commit()


def ingest_all(dbname: str) -> None:
    users_csv = ROOT / "my_users.csv"
    checkins_tsv = ROOT / "my_checkins_anonymized.tsv"
    f_before_tsv = ROOT / "my_frienship_before.tsv"
    f_after_tsv = ROOT / "my_frienship_after.tsv"
    pois_tsv = ROOT / "my_POIs.tsv"

    for p in [users_csv, checkins_tsv, f_before_tsv, f_after_tsv, pois_tsv]:
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    conn = get_conn(dbname)
    conn.autocommit = False
    build_schema(conn)

    timings = []
    with conn.cursor() as cur:
        started = time.perf_counter()
        copy_file(cur, "COPY users(userid) FROM STDIN WITH (FORMAT csv, HEADER true)", users_csv)
        conn.commit()
        timings.append(("users", time.perf_counter() - started))

        started = time.perf_counter()
        copy_file(
            cur,
            "COPY pois(poi_id, latitude, longitude, category, country) "
            "FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', HEADER false)",
            pois_tsv,
        )
        conn.commit()
        timings.append(("pois", time.perf_counter() - started))

        started = time.perf_counter()
        copy_file(
            cur,
            "COPY checkins(userid, poi_id, checkin_time_text, tz_offset_minutes) "
            "FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', HEADER false)",
            checkins_tsv,
        )
        conn.commit()
        timings.append(("checkins", time.perf_counter() - started))

        started = time.perf_counter()
        copy_file(
            cur,
            "COPY friendship_before(userid, friendid) "
            "FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', HEADER false)",
            f_before_tsv,
        )
        conn.commit()
        timings.append(("friendship_before", time.perf_counter() - started))

        started = time.perf_counter()
        copy_file(
            cur,
            "COPY friendship_after(userid, friendid) "
            "FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', HEADER false)",
            f_after_tsv,
        )
        conn.commit()
        timings.append(("friendship_after", time.perf_counter() - started))

    total = sum(x[1] for x in timings)
    print("\nCitus ingestion timing (seconds):")
    for name, sec in timings:
        print(f"  {name:18s} {sec:10.2f}")
    print(f"  {'TOTAL':18s} {total:10.2f}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest Foursquare slice into Citus")
    parser.add_argument("--dbname", default="foursquaredb")
    parser.add_argument(
        "--skip-create-db",
        action="store_true",
        help="Do not attempt CREATE DATABASE; use existing db only.",
    )
    args = parser.parse_args()

    if not args.skip_create_db:
        ensure_database(args.dbname)
    ingest_all(args.dbname)


if __name__ == "__main__":
    main()
