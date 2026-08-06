with source as (
    select * from {{ source('pokeapi', 'raw_pokemon_types') }}
)

select
    pokemon_id,
    type_id,
    slot        as type_slot

from source
