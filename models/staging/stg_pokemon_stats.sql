with source as (
    select * from {{ source('pokeapi', 'raw_pokemon_stats') }}
)

select
    pokemon_id,
    stat_id,
    base_stat,
    effort         as effort_value

from source
