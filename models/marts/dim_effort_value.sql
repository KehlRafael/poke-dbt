with pokemon as (
    select * from {{ ref('stg_pokemon') }}
),

stats as (
    select * from {{ ref('stg_pokemon_stats') }}
),

stat_lookup as (
    select * from {{ ref('stg_stats') }}
)

select
    p.pokemon_id,
    p.pokemon_name,
    p.national_dex,
    sl.stat_name    as stat,
    st.effort_value

from stats st
inner join pokemon p        on st.pokemon_id = p.pokemon_id
inner join stat_lookup sl   on st.stat_id = sl.stat_id
