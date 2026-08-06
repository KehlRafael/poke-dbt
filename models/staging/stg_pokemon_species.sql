with source as (
    select * from {{ source('pokeapi', 'raw_pokemon_species') }}
)

select
    id                                      as species_id,
    identifier                              as species_name,
    generation_id,
    evolves_from_species_id,
    capture_rate,
    base_happiness,
    cast(is_baby as boolean)                as is_baby,
    cast(is_legendary as boolean)           as is_legendary,
    cast(is_mythical as boolean)            as is_mythical

from source
