with source as (
    select * from {{ source('pokeapi', 'raw_abilities') }}
)

select
    id                          as ability_id,
    identifier                  as ability_name,
    generation_id,
    cast(is_main_series as boolean) as is_main_series

from source
