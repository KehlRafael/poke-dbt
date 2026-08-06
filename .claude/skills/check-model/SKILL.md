---
name: check-model
description: Validate that this dbt project (poke-dbt) still builds and tests cleanly, and that models follow the conventions in CLAUDE.md - one yml per model/source with full column documentation, PK unique/not_null, FK not_null/relationships, sources kept out of models/staging/. Use whenever the user asks to check, validate, or review a new dbt model, or wants to confirm the project is in a good state. Scopes to the new model(s) ahead of main when one exists, otherwise checks the whole project. Reports issues with concrete guidance - never edits files to fix them.
---

# check-model

Validate that a dbt model in this project builds, tests cleanly, and follows the
conventions documented in `CLAUDE.md`. This skill only reports problems and how to
fix them - it never edits model, yml, or config files itself. If something is
broken, the person who wrote the model fixes it and re-runs the skill.

## 1. Decide the scope: a specific new model, or the whole project

Determine whether there's a new model to focus on:

```bash
git rev-parse --abbrev-ref HEAD
git log main..HEAD --oneline
```

- If the current branch has commits ahead of `main`, inspect what they touched:
  `git diff --name-status main...HEAD -- models/`. Look for newly added `.sql`
  files under `models/staging/`, `models/intermediate/`, or `models/marts/`.
- If one or more new models are found this way, **scope the check to those
  models** (see step 3 for the exact selector).
- If there are no commits ahead of `main`, or none of them add a new model file,
  **scope the check to the whole project** — every model and every source.

Don't go looking for uncommitted changes to widen this decision; the trigger is
specifically commits ahead of `main`, as that's what distinguishes "someone just
added a model" from "just run the usual checks."

## 2. Make sure the environment can actually build

```bash
uv run python scripts/load_raw_data.py --check
```

If any `raw_*` table is missing, tell the user to run
`uv run python scripts/load_raw_data.py` themselves before continuing — do not
run it for them. Loading the raw layer is a prerequisite step, not something
this skill silently fixes on the user's behalf.

## 3. Build and test

```bash
export DBT_PROFILES_DIR=.
uv run dbt deps
```

Then, depending on the scope from step 1:

- **Whole project**: `uv run dbt build`
- **Specific new model(s)**: `uv run dbt build --select +<model_name>+` for each new
  model (the `+` on both sides pulls in its full ancestor and descendant chain,
  since a new model can break things downstream, or reveal that something it
  depends on isn't in the state this model assumes).

Report the raw pass/fail/warn counts. A `WARN` on
`dbt_utils_accepted_range_dim_pokemon_stat_total__800__100` is expected — see
`CLAUDE.md`'s Technical notes (Eternatus-Eternamax genuinely scores 1125). Any
other `WARN` or any `ERROR` is a real finding to report, not something to
dismiss or fix inline.

## 4. Check the model(s) against CLAUDE.md's conventions

Re-read `CLAUDE.md`'s **Conventions** section first — it's the source of truth,
don't rely on memory of past runs. For each model in scope, check:

- **File placement**: does `models/<layer>/<model>.sql` have exactly one sibling
  `models/<layer>/<model>.yml`? No grouped yml files, no underscore prefixes.
- **Documentation completeness**: run the helper script, which mechanically
  diffs each table's real columns (from `data/pokedex.duckdb`) against what's
  documented in its yml:

  ```bash
  uv run python .claude/skills/check-model/scripts/check_docs.py <model_name>   # or with no args to check everything in scope
  ```

  This flags: missing top-level description, columns present in the table but
  undocumented, columns documented but with a blank description, and stale yml
  columns that no longer exist in the table. It's read-only and only reports —
  treat its output as findings to relay, not to act on yourself.
- **Test coverage**: read the model's yml directly and reason about it against
  the convention (this needs judgment the script doesn't have — e.g. recognizing
  that `species_id` is a foreign key requires knowing what it means, not just
  its name):
  - Primary key column(s) have `unique` + `not_null`.
  - Foreign key column(s) have `not_null` + `relationships` pointing at the
    correct parent (`source(...)` for a source-layer FK, `ref(...)` for a
    staging-layer FK).
  - If this is a staging model, the same key/relationship tests that exist on
    its source table are mirrored here (per CLAUDE.md: "a broken assumption is
    caught at the layer closest to where it actually breaks").
- **Naming and layer conventions**: `stg_` for staging, `int_` for intermediate;
  for marts, `fct_` only for event/process-grain tables with measures, `dim_`
  for entity-grain tables with descriptive attributes (don't default to `fct_`
  for everything in `models/marts/`). Materialization/schema should match the
  layer in `dbt_project.yml`: staging = table in `stg`, intermediate = view in
  `pokedex`, marts = table in `pokedex`. Raw sources live in the `raw` schema
  (loaded directly by `scripts/load_raw_data.py`, not by dbt).
- **Sources stay out of `models/staging/`**: if the new model is a source
  declaration, its yml belongs under `models/sources/`, one file per raw table.

## 5. Report

Give the user a plain list, grouped by model/table:

- What was checked (scope: specific model(s) or whole project, and why).
- Build/test result (pass/fail/warn counts; call out anything beyond the known
  expected warn).
- Each convention violation found, with the exact file and column/test affected,
  and a one-line suggestion of what to add or change — described in words, not
  applied as an edit.
- If everything passes and nothing is missing, say so plainly and stop; don't
  pad a clean result with suggestions that weren't asked for.
