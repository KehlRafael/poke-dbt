-- Reconciliation test: every Pokémon in dim_pokemon must have at least one
-- EV yield row in dim_effort_value. Fails by returning the Pokémon that don't.

with pokemon as (
    select * from {{ ref('dim_pokemon') }}
),

ev_yields as (
    select distinct pokemon_id from {{ ref('dim_effort_value') }}
)

select
    p.pokemon_id,
    p.pokemon_name
from pokemon p
left join ev_yields ev on p.pokemon_id = ev.pokemon_id
where ev.pokemon_id is null
