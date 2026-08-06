# pokedex — a dbt toy project on PokeAPI data

Raw relational Pokémon data (all 9 generations) turned into a small, testable
dbt pipeline. Built as companion material for an entry-level dbt talk.

## 1. Get the data

```bash
pip install duckdb
python scripts/load_raw_data.py            # first run: downloads all 9 CSVs into data/, loads data/pokedex.duckdb
python scripts/load_raw_data.py            # re-run any time: only re-downloads changed files
python scripts/load_raw_data.py --check    # just report status, no download
```

This creates `data/pokedex.duckdb` with the raw PokeAPI tables (`raw_pokemon`,
`raw_pokemon_species`, ...), which dbt reads directly as sources.

## 2. Set up dbt

Requires a warehouse to point dbt at — DuckDB is the easiest zero-install option
for a demo:

```bash
pip install dbt-duckdb
export DBT_PROFILES_DIR=.   # profiles.yml lives in the project root - no global ~/.dbt/ setup needed
dbt deps          # installs dbt_utils, used by several tests/macros below
dbt run           # builds staging -> intermediate -> marts
dbt test          # runs all schema tests
```

(Alternatively, skip the `export` and pass `--profiles-dir .` on each `dbt` command.)

## Project layout

```
data/
  *.csv                      the 9 raw PokeAPI CSVs (gitignored, see load_raw_data.py)
  pokedex.duckdb             DuckDB file: raw_* tables (loaded by the script) + all dbt-built models (gitignored)
profiles.yml                 DuckDB target, kept in the project - no global ~/.dbt/ setup needed
models/
  sources/                   one raw_*.yml per raw source table (dbt source declarations only)
  staging/                   1:1 with each raw_* source table - renaming, casting, light cleanup
                              each staging model has its own .yml (docs + tests)
  intermediate/               int_pokemon_stats_pivoted - long -> wide via Jinja loop
  marts/                      fct_pokemon - the denormalized, presentation-ready table
macros/
  pivot_long_to_wide.sql      generic long->wide pivot, column list resolved at compile time
  stat_tier.sql               parameterized bucketing logic (stat_total -> S/A/B/C/D)
scripts/
  load_raw_data.py            downloads the PokeAPI CSVs and loads them into DuckDB as raw_* tables
```

## What each piece is there to demonstrate

| Feature | Where |
|---|---|
| Sources | `models/sources/raw_*.yml` + `data/pokedex.duckdb` (loaded by `scripts/load_raw_data.py`) |
| Staging pattern (1 source -> 1 staging model) | `models/staging/` |
| Joins (1:many, many:many) | `stg_pokemon -> stg_pokemon_species` (many:1), `stg_pokemon_types` / `stg_pokemon_abilities` (many:many bridges) |
| Schema tests: not_null, unique, relationships, accepted_values | `models/staging/stg_*.yml` |
| Custom singular/combo tests via dbt_utils | `dbt_utils.unique_combination_of_columns` on the bridge tables |
| Jinja loop generating SQL at compile time | `macros/pivot_long_to_wide.sql` (loops over `run_query` results) |
| Reusable parameterized macro | `macros/stat_tier.sql` |
| Derived business logic (stat_total, stat_tier) computed in dbt, not the source | `models/marts/fct_pokemon.sql` |
| Fan-out awareness (forms vs species) | `stg_pokemon_forms` intentionally kept separate - good talking point on join cardinality |

## Notes / adapter caveats

- The pivot macro fetches its column list via `run_query` at compile time, so
  `dbt compile`/`dbt run` needs a live connection to a `data/pokedex.duckdb` that
  already has the `raw_*` tables loaded — run `scripts/load_raw_data.py` first.
