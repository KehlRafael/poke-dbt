# CLAUDE.md — poke-dbt project

Project guidelines for working in this repo. It's a general-purpose dbt reference
project meant to demonstrate core dbt concepts — sources, staging, joins, Jinja macros,
schema tests, derived business logic — on a small, genuinely relational dataset.

## What this project is

A dbt project that turns PokeAPI's raw relational CSV export into a tested,
layered pipeline: raw source tables → staging → intermediate → marts. It's meant
to be read, run, and extended as reference/learning material.

## Data source

Data comes from **PokeAPI's own raw CSV export**
(`github.com/PokeAPI/pokeapi`, `data/v2/csv/`), not a pre-enriched/flattened
dataset. This is a deliberate design constraint to preserve:
- The data is genuinely relational/normalized (not one wide flat table), so joins
  in this project are real, not decorative.
- Base stats ship in **long format** (`pokemon_stats.csv`). Pivoting to wide and
  computing `stat_total`/`stat_tier` happens *in dbt*, not in the source data —
  keep derived values computed in the pipeline, not pre-baked into seed/source data.
- Covers all generations and is actively maintained upstream.

## The 9 raw tables in use (out of ~50 available in the PokeAPI dump)

`scripts/load_raw_data.py` downloads these as CSVs (cached in `data/`) and loads
each into `data/pokedex.duckdb`'s `raw` schema as a `raw_*` table, declared as
a dbt source.

| CSV | Raw table | Grain | Notes |
|---|---|---|---|
| `pokemon.csv` | `raw_pokemon` | one row per form/variant | leaf entity; includes non-default forms (megas, regional variants) sharing a `species_id` — intentional, not a bug |
| `pokemon_species.csv` | `raw_pokemon_species` | one row per species | generation, evolution chain, legendary/mythical/baby flags |
| `pokemon_forms.csv` | `raw_pokemon_forms` | one row per cosmetic/battle form | sits between species and pokemon; many rows can share one `pokemon_id` (Unown, Vivillon, ...) |
| `pokemon_stats.csv` | `raw_pokemon_stats` | long format, (pokemon_id, stat_id) | pivoted downstream, not pre-aggregated |
| `stats.csv` | `raw_stats` | lookup | drives the pivot macro's column names |
| `pokemon_types.csv` | `raw_pokemon_types` | many:many bridge, slot 1/2 | |
| `types.csv` | `raw_types` | lookup | |
| `pokemon_abilities.csv` | `raw_pokemon_abilities` | many:many bridge, slot 1/2/3 (3 = hidden) | |
| `abilities.csv` | `raw_abilities` | lookup | |

Not included: `pokemon_moves.csv` (large move-list table) and
`egg_groups`/`pokemon_egg_groups` (a second many:many bridge) — both are valid
candidates for extending this project, but are out of scope today.

## Schema layout

Each layer lives in its own DuckDB schema, within the single `data/pokedex.duckdb` file:

| Schema | Layer | Materialization |
|---|---|---|
| `raw` | raw source tables | tables, loaded directly by `scripts/load_raw_data.py` (not dbt) |
| `stg` | staging | tables |
| `pokedex` | intermediate, marts | intermediate = views, marts = tables |

`macros/generate_schema_name.sql` overrides dbt's default schema-naming macro
so a model's `+schema: stg` config produces a literal `stg` schema instead of
dbt's default `<target_schema>_stg` concatenation.

## Project structure

```
poke-dbt/
├── scripts/load_raw_data.py       # downloads the 9 CSVs from PokeAPI's repo into data/, loads them into the raw schema of data/pokedex.duckdb
├── data/
│   ├── *.csv                      # cached raw CSVs (gitignored)
│   └── pokedex.duckdb             # raw/stg/pokedex schemas: raw_* tables + all dbt-built models (gitignored)
├── models/
│   ├── sources/                   # one raw_<table>.yml per raw source table - dbt source declarations only, no models
│   ├── staging/                   # 9 models, 1:1 with each raw_* source table, light renaming/casting
│   │                              # each staging model has its own <model>.yml
│   ├── intermediate/
│   │   ├── int_pokemon_stats_pivoted.sql   # long -> wide via pivot_long_to_wide macro
│   │   └── int_pokemon_stats_pivoted.yml
│   └── marts/
│       ├── dim_pokemon.sql        # denormalized: species + types + abilities (ability_1/2/hidden_ability) + wide stats + forms_list + stat_total + stat_tier
│       └── dim_pokemon.yml
├── macros/
│   ├── pivot_long_to_wide.sql     # generic long->wide pivot; resolves pivot columns at COMPILE time via run_query
│   ├── stat_tier.sql              # parameterized S/A/B/C/D bucketing on stat_total
│   └── generate_schema_name.sql   # makes custom +schema config (stg) literal, not target_schema-prefixed
├── dbt_project.yml
├── packages.yml                   # dbt_utils (used for unique_combination_of_columns, accepted_range)
├── profiles.yml                   # DuckDB target, kept in the project - run dbt with --profiles-dir . / DBT_PROFILES_DIR=.
└── README.md                      # setup steps + feature-to-file mapping table
```

## Conventions

- **YAML files are per-model/per-source, never grouped**, and never prefixed with
  an underscore: each staging/intermediate/marts model has its own `<model>.yml`
  next to its `.sql` file; each raw source table has its own `raw_<table>.yml`
  under `models/sources/`.
- **Sources live in `models/sources/`, separate from `models/staging/`** — sources
  are declarations of external raw tables, not staging models, and shouldn't be
  mixed into the same directory.
- **Each layer has its own schema** (see Schema layout above): `raw` for source
  tables, `stg` for staging, `pokedex` for intermediate/marts. A new staging
  model doesn't need a `+schema` override - it inherits `stg` from
  `dbt_project.yml`.
- **Testing is layered and consistent**: every primary key gets `unique` +
  `not_null`; every foreign key gets `not_null` + `relationships`. These tests are
  applied at the source layer *and* mirrored at the staging layer that consumes
  each source, so a broken assumption is caught at the layer closest to where it
  actually breaks.
- **`dim_pokemon` includes every Pokémon form/variant**, not just default forms
  (`is_default_form = true`) — this is current, intended behavior, not a
  filter that's pending implementation.
- **Naming follows fact/dimension semantics**: `dim_pokemon` is a dimension
  (`dim_` prefix), not a fact — it's one row per entity with descriptive
  attributes, not a log of business events with measures. `fct_`/`dim_` should
  be chosen based on that distinction, not applied by default to every mart.
- **Every model and source table is fully documented**: a top-level
  `description`, plus a `description` on every column the model/table actually
  exposes — not just the columns that happen to carry a test.

## Technical notes

- The `pivot_long_to_wide` macro queries `stg_stats` live at compile time via
  `run_query`, so `dbt compile`/`dbt run` needs `scripts/load_raw_data.py` to have
  loaded the raw tables first.
- `pokemon_species.evolves_from_species_id` and `pokemon_forms.form_order` need to
  stay `varchar` (blank values break DuckDB's type inference otherwise) — pinned
  via `COLUMN_TYPE_OVERRIDES` in `scripts/load_raw_data.py`.
- `dim_pokemon.stat_total`'s `accepted_range` test (100-800) runs at
  `severity: warn`, not `error` — Eternatus-Eternamax legitimately scores 1125
  in-game, so it's a genuine data point rather than a data-quality bug.

## Running the project

```bash
uv run python scripts/load_raw_data.py     # download + load raw_* tables into data/pokedex.duckdb
export DBT_PROFILES_DIR=.                  # profiles.yml lives in the project root
uv run dbt deps && uv run dbt build        # builds every model and runs every test, in DAG order
```

Requires [uv](https://docs.astral.sh/uv/) — dependencies are declared in
`pyproject.toml`/`uv.lock`, `uv run` installs them automatically.

Current state: 11 models, 9 sources, 73 data tests (72 pass, 1 expected `warn` —
see the `stat_total` note above).
