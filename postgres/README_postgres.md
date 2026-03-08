# PostgreSQL Part (Assignment I)

## 1) Install PostgreSQL 17.9 on macOS

Option A (official installer, usually `/Library/PostgreSQL/17`):

```bash
echo 'export PATH="/Library/PostgreSQL/17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Option B (Homebrew):

```bash
brew install postgresql@17
brew services start postgresql@17
```

Add binaries to shell PATH:

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Check:

```bash
psql --version
```

## 2) Python environment

From project root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install psycopg2-binary
```

## 3) Configure DB connection (optional)

Default connection values used by scripts:
- `PGHOST=localhost`
- `PGPORT=5432`
- `PGUSER=postgres`
- `PGPASSWORD=""` (empty)

If your user is different:

```bash
export PGUSER="<your_pg_user>"
export PGPASSWORD="<your_password_if_any>"
```

## 4) Ingestion

From project root:

```bash
source venv/bin/activate
python postgres/ingest_postgres.py --dbname foursquaredb
```

What this script does:
- creates DB `foursquaredb` if needed
- recreates schema from `postgres/schema_postgres.sql`
- bulk loads `my_users.csv`, `my_POIs.tsv`, `my_checkins_anonymized.tsv`,
  `my_frienship_before.tsv`, `my_frienship_after.tsv`
- prints per-table and total ingestion time

## 5) Run analytical queries (Q1-Q4)

```bash
source venv/bin/activate
python postgres/run_queries_postgres.py --dbname foursquaredb --runs 3 --q4-category Club
```

This prints:
- runtime for each run
- average runtime per query
- sample output rows

## 6) Report screenshots checklist

- terminal command + output for:
  - `python postgres/ingest_postgres.py ...`
  - `python postgres/run_queries_postgres.py ...`
- schema file `postgres/schema_postgres.sql`
- script files:
  - `postgres/ingest_postgres.py`
  - `postgres/run_queries_postgres.py`
- result outputs for Q1, Q2, Q3, Q4
