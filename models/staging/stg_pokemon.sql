with source as (
    select * from {{ source('pokeapi', 'raw_pokemon') }}
)

select
    id                                  as pokemon_id,
    identifier                          as pokemon_name,
    species_id                          as national_dex,
    height                              as height_decimetres,
    weight                              as weight_hectograms,
    base_experience,
    "order"                             as national_order,
    cast(is_default as boolean)         as is_default_form

from source
