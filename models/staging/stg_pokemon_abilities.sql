with source as (
    select * from {{ source('pokeapi', 'raw_pokemon_abilities') }}
)

select
    pokemon_id,
    ability_id,
    slot                        as ability_slot,
    cast(is_hidden as boolean)  as is_hidden_ability

from source
