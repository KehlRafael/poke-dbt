#!/usr/bin/env python3
"""
check_docs.py

Mechanical, read-only diff between what a table actually looks like in
data/pokedex.duckdb and what its <name>.yml says about it. Covers both dbt
models (models/staging|intermediate|marts/<name>.sql + <name>.yml) and raw
sources (models/sources/raw_<name>.yml, no .sql - the table is loaded by
scripts/load_raw_data.py).

This script does not fix anything. It only reports gaps for a human (or the
calling skill) to act on.

Usage (run from the project root, after `dbt build`):
    python .claude/skills/check-model/scripts/check_docs.py               # check everything
    python .claude/skills/check-model/scripts/check_docs.py stg_pokemon   # check specific table(s)
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import yaml

PROJECT_ROOT = Path.cwd()
DB_PATH = PROJECT_ROOT / "data" / "pokedex.duckdb"
MODELS_DIR = PROJECT_ROOT / "models"


def load_yaml_entries() -> dict[str, dict]:
    """Scan every models/**/*.yml file and index each documented model/source table by name."""
    entries: dict[str, dict] = {}

    for yml_path in sorted(MODELS_DIR.rglob("*.yml")):
        try:
            doc = yaml.safe_load(yml_path.read_text()) or {}
        except yaml.YAMLError as exc:
            print(f"  ! could not parse {yml_path.relative_to(PROJECT_ROOT)}: {exc}")
            continue

        for model in doc.get("models", []):
            name = model.get("name")
            if not name:
                continue
            entries[name] = {
                "kind": "model",
                "yml_path": yml_path,
                "description": model.get("description"),
                "columns": {
                    col.get("name"): col.get("description")
                    for col in model.get("columns", [])
                    if col.get("name")
                },
            }

        for source in doc.get("sources", []):
            for table in source.get("tables", []):
                name = table.get("name")
                if not name:
                    continue
                entries[name] = {
                    "kind": "source",
                    "yml_path": yml_path,
                    "description": table.get("description"),
                    "columns": {
                        col.get("name"): col.get("description")
                        for col in table.get("columns", [])
                        if col.get("name")
                    },
                }

    return entries


def actual_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> list[str] | None:
    # Raw tables live in `raw`, staging in `stg`, intermediate/marts in `pokedex` -
    # table names are unique across the project, so match on name alone.
    rows = con.execute(
        "select column_name from information_schema.columns "
        "where table_name = ? "
        "order by ordinal_position",
        [table_name],
    ).fetchall()
    return [r[0] for r in rows] if rows else None


def check_model_file_placement(entries: dict[str, dict]) -> list[str]:
    """Every model .sql file should have exactly one sibling <name>.yml documenting it."""
    issues = []
    for layer in ("staging", "intermediate", "marts"):
        layer_dir = MODELS_DIR / layer
        if not layer_dir.exists():
            continue
        for sql_file in sorted(layer_dir.glob("*.sql")):
            name = sql_file.stem
            expected_yml = layer_dir / f"{name}.yml"
            if name not in entries:
                issues.append(
                    f"{sql_file.relative_to(PROJECT_ROOT)} has no documenting yml "
                    f"(expected {expected_yml.relative_to(PROJECT_ROOT)})"
                )
            elif entries[name]["yml_path"] != expected_yml:
                issues.append(
                    f"{name} is documented in "
                    f"{entries[name]['yml_path'].relative_to(PROJECT_ROOT)} instead of "
                    f"{expected_yml.relative_to(PROJECT_ROOT)} (one yml per model, no grouping)"
                )

    for yml_path in MODELS_DIR.rglob("*.yml"):
        if yml_path.name.startswith("_"):
            issues.append(
                f"{yml_path.relative_to(PROJECT_ROOT)} is prefixed with an underscore "
                f"(project convention is no underscore-prefixed yml files)"
            )

    return issues


def diff_table(name: str, entry: dict, con: duckdb.DuckDBPyConnection) -> list[str]:
    problems = []
    cols = actual_columns(con, name)

    if cols is None:
        problems.append(f"table '{name}' not found in data/pokedex.duckdb (build it first)")
        return problems

    if not entry.get("description"):
        problems.append(f"missing top-level description in {entry['yml_path'].name}")

    documented = entry["columns"]
    undocumented = [c for c in cols if c not in documented]
    if undocumented:
        problems.append(f"columns present in the table but not documented: {undocumented}")

    stale = [c for c in documented if c not in cols]
    if stale:
        problems.append(f"columns documented but no longer in the table (stale docs): {stale}")

    blank_desc = [c for c, desc in documented.items() if c in cols and not desc]
    if blank_desc:
        problems.append(f"columns documented with no description: {blank_desc}")

    return problems


def main() -> int:
    requested = sys.argv[1:]

    if not DB_PATH.exists():
        print(f"No database at {DB_PATH.relative_to(PROJECT_ROOT)} - run `dbt build` first.")
        return 1

    entries = load_yaml_entries()
    placement_issues = check_model_file_placement(entries)

    targets = requested if requested else sorted(entries)
    unknown = [t for t in targets if t not in entries]
    if unknown:
        print(f"Not documented anywhere under models/: {unknown}")

    any_issue = bool(placement_issues) or bool(unknown)

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        for name in targets:
            if name not in entries:
                continue
            problems = diff_table(name, entries[name], con)
            if problems:
                any_issue = True
                print(f"\n{name} ({entries[name]['kind']}, {entries[name]['yml_path'].relative_to(PROJECT_ROOT)}):")
                for p in problems:
                    print(f"  - {p}")

    if placement_issues:
        print("\nFile placement / naming issues:")
        for p in placement_issues:
            print(f"  - {p}")

    if not any_issue:
        print("No documentation gaps found.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
