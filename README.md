# poke-dbt — a dbt project on PokeAPI data

Raw relational Pokémon data (all 9 generations) turned into a small, tested dbt
pipeline: raw source tables → staging → intermediate → marts.

Requires [uv](https://docs.astral.sh/uv/). Dependencies are declared in
`pyproject.toml`/`uv.lock` — `uv run` installs them automatically on first use.

## 1. Get the data

```bash
uv run python scripts/load_raw_data.py            # first run: downloads all 9 CSVs into data/, loads data/pokedex.duckdb
uv run python scripts/load_raw_data.py            # re-run any time: only re-materializes changed files
uv run python scripts/load_raw_data.py --check    # just downloads and report status, no materialization
```

This creates `data/pokedex.duckdb` with the raw PokeAPI tables (`raw_pokemon`,
`raw_pokemon_species`, ...), which dbt reads directly as sources.

## 2. Set up dbt

DuckDB is the target — zero-install, no external warehouse needed:

```bash
export DBT_PROFILES_DIR=.   # profiles.yml lives in the project root
uv run dbt deps             # installs dbt_utils, used by several tests/macros below
uv run dbt build            # builds every model and runs every test, in DAG order
```

Alternatively, you can skip the `export` and pass `--profiles-dir .` on each `dbt` command.

## 3. Browse the docs

```bash
uv run dbt docs generate
uv run dbt docs serve
```

Opens a browsable site with every model/source description, column doc, test,
and the full DAG — generated straight from the yml files under `models/`.

## 4. Check new development

Before committing a new or changed model, run the `check-model` skill:

```
/check-model
```

It builds and tests the project (or just the new model and its dependency
chain, if one is ahead of `main`), then checks the result against the
conventions in `CLAUDE.md` — per-model yml docs, column-level descriptions,
PK/FK test coverage, source placement. It only reports what it finds; so
that you can fix the issues.

## Project layout

```
├── data/                    raw CSVs + pokedex.duckdb (gitignored)
├── profiles.yml             dbt profile, kept in-project
├── models/
│   ├── sources/             raw_*.yml source declarations
│   ├── staging/             1:1 cleanup per source
│   ├── intermediate/        reusable, complex logic
│   └── marts/               ready for consumption
├── macros/
│   ├── pivot_long_to_wide.sql
│   └── stat_tier.sql
├── scripts/
│   └── load_raw_data.py     loads raw_* tables into DuckDB
└── .claude/skills/
    └── check-model/         validates new models (step 4)
```

## Feature map

| Feature | Where |
|---|---|
| Sources | `models/sources/raw_*.yml` + `data/pokedex.duckdb` (loaded by `scripts/load_raw_data.py`) |
| Staging pattern (1 source -> 1 staging model) | `models/staging/` |
| Joins (1:many, many:many) | `stg_pokemon -> stg_pokemon_species` (many:1), `stg_pokemon_types` / `stg_pokemon_abilities` (many:many bridges) |
| Schema tests: not_null, unique, relationships, accepted_values | `models/staging/stg_*.yml` |
| Custom singular/combo tests via dbt_utils | `dbt_utils.unique_combination_of_columns` on the bridge tables |
| Jinja loop generating SQL at compile time | `macros/pivot_long_to_wide.sql` (loops over `run_query` results) |
| Reusable parameterized macro | `macros/stat_tier.sql` |
| Derived business logic (stat_total, stat_tier) computed in dbt, not the source | `models/marts/dim_pokemon.sql` |
| Fan-out (forms vs species) | `stg_pokemon_forms` is many-to-one with `stg_pokemon`, kept as a separate model rather than pre-joined |

## Notes / adapter caveats

- The pivot macro fetches its column list via `run_query` at compile time, so
  `dbt compile`/`dbt build` needs a live connection to a `data/pokedex.duckdb` that
  already has the `raw_*` tables loaded — run `scripts/load_raw_data.py` first.
