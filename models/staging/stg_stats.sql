with source as (
    select * from {{ source('pokeapi', 'raw_stats') }}
)

select
    id             as stat_id,
    identifier     as stat_name

from source
