#!/usr/bin/env python3
"""
load_raw_data.py

Downloads the raw PokeAPI CSV exports and loads them into DuckDB as raw_*
tables, ready to be declared as dbt sources.

Source of truth: https://github.com/PokeAPI/pokeapi (data/v2/csv/*.csv)

Usage:
    python scripts/load_raw_data.py                 # downloads only CSVs missing from the cache
    python scripts/load_raw_data.py --yes           # re-downloads and overwrites every target CSV
    python scripts/load_raw_data.py --check         # only report status, no network calls at all
    python scripts/load_raw_data.py --files pokemon.csv stats.csv   # limit to specific files

CSVs are cached in <project_root>/data/. Once a CSV is cached, it's reused as-is
on every future run (per PokeAPI's fair use policy - https://pokeapi.co/docs/v2#fairuse
- "Locally cache resources whenever you request them") and is never re-requested
from PokeAPI unless --yes is passed. Each cached CSV is loaded into
<project_root>/data/pokedex.duckdb, schema `raw`, as a table named
raw_<file stem>, e.g. pokemon.csv -> raw.raw_pokemon.
"""

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import duckdb

RAW_BASE = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv"

# The 9 files that make up the toy project's raw layer.
RAW_FILES = [
    "pokemon.csv",
    "pokemon_species.csv",
    "pokemon_forms.csv",
    "pokemon_stats.csv",
    "stats.csv",
    "pokemon_types.csv",
    "types.csv",
    "pokemon_abilities.csv",
    "abilities.csv",
]

# A couple of columns need to stay varchar - blank values in the raw CSVs
# would otherwise trip DuckDB's type inference.
COLUMN_TYPE_OVERRIDES = {
    "pokemon_species.csv": {"evolves_from_species_id": "VARCHAR"},
    "pokemon_forms.csv": {"form_order": "VARCHAR"},
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "pokedex.duckdb"
RAW_SCHEMA = "raw"


def raw_table_name(filename: str) -> str:
    return f"raw_{Path(filename).stem}"


def qualified_table_name(filename: str) -> str:
    return f"{RAW_SCHEMA}.{raw_table_name(filename)}"


def download(filename: str) -> bytes:
    url = f"{RAW_BASE}/{filename}"
    with urlopen(url, timeout=30) as resp:  # noqa: S310 - fixed trusted host
        return resp.read()


def sync_csv(filename: str, *, force: bool) -> str:
    """Ensures filename is present in DATA_DIR, downloading only if missing or forced.

    Never re-requests an already-cached file unless force=True - PokeAPI's fair
    use policy asks consumers to locally cache resources whenever they're requested.
    """
    dest = DATA_DIR / filename
    exists = dest.exists()
    if exists and not force:
        return "cached"

    try:
        remote_bytes = download(filename)
    except (HTTPError, URLError) as exc:
        return f"ERROR ({exc})"

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(remote_bytes)
    return "refreshed" if exists else "downloaded"


def load_table(con: duckdb.DuckDBPyConnection, filename: str) -> int:
    """Loads DATA_DIR/filename into raw.raw_<name> in the DuckDB file. Returns the row count."""
    csv_path = DATA_DIR / filename
    table = qualified_table_name(filename)
    overrides = COLUMN_TYPE_OVERRIDES.get(filename)
    types_clause = ""
    if overrides:
        pairs = ", ".join(f"'{col}': '{dtype}'" for col, dtype in overrides.items())
        types_clause = f", types={{{pairs}}}"

    con.execute(f"create schema if not exists {RAW_SCHEMA}")
    con.execute(
        f"create or replace table {table} as "
        f"select * from read_csv_auto('{csv_path.as_posix()}'{types_clause})"
    )
    return con.execute(f"select count(*) from {table}").fetchone()[0]


def check(targets: list[str]) -> int:
    print(f"Data cache: {DATA_DIR}")
    print(f"DuckDB file: {DB_PATH}\n")

    table_counts = {}
    if DB_PATH.exists():
        with duckdb.connect(str(DB_PATH), read_only=True) as con:
            existing = {
                row[0]
                for row in con.execute(
                    "select table_name from information_schema.tables where table_schema = ?",
                    [RAW_SCHEMA],
                ).fetchall()
            }
            for filename in targets:
                table = raw_table_name(filename)
                if table in existing:
                    table_counts[table] = con.execute(
                        f"select count(*) from {qualified_table_name(filename)}"
                    ).fetchone()[0]

    for filename in targets:
        table = raw_table_name(filename)
        csv_status = "cached" if (DATA_DIR / filename).exists() else "MISSING"
        db_status = f"{table_counts[table]} rows" if table in table_counts else "MISSING"
        print(f"  {filename:<28} csv: {csv_status:<10} duckdb.{RAW_SCHEMA}.{table}: {db_status}")

    missing = [f for f in targets if raw_table_name(f) not in table_counts]
    if missing:
        print(f"\n{len(missing)} table(s) not loaded yet: {missing}")
        return 1

    print("\nAll raw tables loaded.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("Usage:")[0])
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Re-download and overwrite cached CSVs, even if already present.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Only report status; do not download or load.",
    )
    parser.add_argument(
        "--files", nargs="+", default=None,
        help="Limit the operation to specific filenames (default: all 9 raw files).",
    )
    args = parser.parse_args()

    targets = args.files if args.files else RAW_FILES
    unknown = [f for f in targets if f not in RAW_FILES]
    if unknown:
        print(f"Unknown file(s) requested (not part of this project's raw layer): {unknown}")
        return 1

    if args.check:
        return check(targets)

    print(f"Data cache: {DATA_DIR}")
    print(f"DuckDB file: {DB_PATH}")
    print(f"Syncing and loading {len(targets)} table(s) from PokeAPI...\n")

    results = {}
    with duckdb.connect(str(DB_PATH)) as con:
        for filename in targets:
            status = sync_csv(filename, force=args.yes)
            results[filename] = status

            if status.startswith("ERROR"):
                print(f"  {filename:<28} {status}")
                continue

            row_count = load_table(con, filename)
            table = qualified_table_name(filename)
            print(f"  {filename:<28} {status:<12} -> {table} ({row_count} rows)")

    failures = [f for f, s in results.items() if s.startswith("ERROR")]
    if failures:
        print(f"\n{len(failures)} file(s) failed: {failures}")
        return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
