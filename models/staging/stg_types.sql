with source as (
    select * from {{ source('pokeapi', 'raw_types') }}
)

select
    id                 as type_id,
    identifier         as type_name,
    generation_id

from source
