#!/usr/bin/env python3
"""
Build custom slice files for the assignment from the full datasets.

Input files expected in the current directory:
  - my_users.csv
  - checkins_anonymized.txt
  - friendship_before_old.txt
  - friendship_after_new.txt
  - POIs.txt

Output files:
  - my_checkins_anonymized.tsv
  - my_frienship_before.tsv
  - my_frienship_after.tsv
  - my_POIs.tsv
"""

import csv
import time
from pathlib import Path


MY_USERS_FILE = Path("my_users.csv")
CHECKINS_FILE = Path("checkins_anonymized.txt")
FRIENDSHIP_BEFORE_FILE = Path("friendship_before_old.txt")
FRIENDSHIP_AFTER_FILE = Path("friendship_after_new.txt")
POIS_FILE = Path("POIs.txt")

OUT_CHECKINS_FILE = Path("my_checkins_anonymized.tsv")
OUT_FRIENDSHIP_BEFORE_FILE = Path("my_frienship_before.tsv")
OUT_FRIENDSHIP_AFTER_FILE = Path("my_frienship_after.tsv")
OUT_POIS_FILE = Path("my_POIs.tsv")


def read_my_user_ids(path: Path) -> set[str]:
    user_ids: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "userid" not in (reader.fieldnames or []):
            raise ValueError("my_users.csv must contain 'userid' column")
        for row in reader:
            user_id = row["userid"].strip()
            if user_id:
                user_ids.add(user_id)
    return user_ids


def filter_checkins(user_ids: set[str], in_path: Path, out_path: Path) -> tuple[int, set[str]]:
    kept = 0
    poi_ids: set[str] = set()
    with in_path.open("r", encoding="utf-8", errors="replace") as fin, out_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 4:
                continue
            user_id, poi_id = parts[0], parts[1]
            if user_id in user_ids:
                fout.write(line if line.endswith("\n") else line + "\n")
                poi_ids.add(poi_id)
                kept += 1
    return kept, poi_ids


def filter_friendships(user_ids: set[str], in_path: Path, out_path: Path) -> int:
    kept = 0
    with in_path.open("r", encoding="utf-8", errors="replace") as fin, out_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 2:
                continue
            user_id, friend_id = parts[0], parts[1]
            if user_id in user_ids and friend_id in user_ids:
                fout.write(line if line.endswith("\n") else line + "\n")
                kept += 1
    return kept


def filter_pois(poi_ids: set[str], in_path: Path, out_path: Path) -> int:
    kept = 0
    with in_path.open("r", encoding="utf-8", errors="replace") as fin, out_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 1:
                continue
            poi_id = parts[0]
            if poi_id in poi_ids:
                fout.write(line if line.endswith("\n") else line + "\n")
                kept += 1
    return kept


def main() -> None:
    started = time.time()
    print("Loading user slice from my_users.csv...")
    user_ids = read_my_user_ids(MY_USERS_FILE)
    print(f"Loaded users: {len(user_ids):,}")

    print("\nFiltering check-ins...")
    checkins_kept, poi_ids = filter_checkins(user_ids, CHECKINS_FILE, OUT_CHECKINS_FILE)
    print(f"Saved {checkins_kept:,} rows -> {OUT_CHECKINS_FILE}")
    print(f"Distinct POIs referenced by your users: {len(poi_ids):,}")

    print("\nFiltering friendships BEFORE snapshot...")
    f_before_kept = filter_friendships(user_ids, FRIENDSHIP_BEFORE_FILE, OUT_FRIENDSHIP_BEFORE_FILE)
    print(f"Saved {f_before_kept:,} rows -> {OUT_FRIENDSHIP_BEFORE_FILE}")

    print("\nFiltering friendships AFTER snapshot...")
    f_after_kept = filter_friendships(user_ids, FRIENDSHIP_AFTER_FILE, OUT_FRIENDSHIP_AFTER_FILE)
    print(f"Saved {f_after_kept:,} rows -> {OUT_FRIENDSHIP_AFTER_FILE}")

    print("\nFiltering POIs used by your users...")
    pois_kept = filter_pois(poi_ids, POIS_FILE, OUT_POIS_FILE)
    print(f"Saved {pois_kept:,} rows -> {OUT_POIS_FILE}")

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.1f} seconds.")


if __name__ == "__main__":
    main()
