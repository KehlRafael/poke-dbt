with source as (
    select * from {{ source('pokeapi', 'raw_pokemon_forms') }}
)

select
    id                                  as form_id,
    form_identifier,
    pokemon_id,
    cast(is_default as boolean)        as is_default_form,
    cast(is_battle_only as boolean)    as is_battle_only_form,
    cast(is_mega as boolean)           as is_mega_form

from source
