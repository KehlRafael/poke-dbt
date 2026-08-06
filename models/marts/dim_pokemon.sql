with pokemon as (
    select * from {{ ref('stg_pokemon') }}
),

species as (
    select * from {{ ref('stg_pokemon_species') }}
),

stats_wide as (
    select * from {{ ref('int_pokemon_stats_pivoted') }}
),

types_agg as (
    select
        pt.pokemon_id,
        max(case when pt.type_slot = 1 then t.type_name end) as primary_type,
        max(case when pt.type_slot = 2 then t.type_name end) as secondary_type
    from {{ ref('stg_pokemon_types') }} pt
    inner join {{ ref('stg_types') }} t on pt.type_id = t.type_id
    group by pt.pokemon_id
),

abilities_agg as (
    select
        pa.pokemon_id,
        max(case when pa.ability_slot = 1 then a.ability_name end) as ability_1,
        max(case when pa.ability_slot = 2 then a.ability_name end) as ability_2,
        max(case when pa.ability_slot = 3 then a.ability_name end) as hidden_ability
    from {{ ref('stg_pokemon_abilities') }} pa
    inner join {{ ref('stg_abilities') }} a on pa.ability_id = a.ability_id
    group by pa.pokemon_id
),

stat_totals as (
    select
        pokemon_id,
        (hp + attack + defense + special_attack + special_defense + speed) as stat_total
    from stats_wide
),

forms_agg as (
    select
        pokemon_id,
        string_agg(form_identifier, ', ' order by form_id) as forms_list
    from {{ ref('stg_pokemon_forms') }}
    group by pokemon_id
)

select
    p.pokemon_id,
    p.pokemon_name,
    p.is_default_form,
    fo.forms_list,
    s.national_dex,
    s.generation_id,
    s.is_legendary,
    s.is_mythical,
    s.is_baby,
    ty.primary_type,
    ty.secondary_type,
    ab.ability_1,
    ab.ability_2,
    ab.hidden_ability,
    sw.hp,
    sw.attack,
    sw.defense,
    sw.special_attack,
    sw.special_defense,
    sw.speed,
    st.stat_total,
    {{ stat_tier('st.stat_total') }} as stat_tier

from pokemon p
inner join species s        on p.national_dex = s.national_dex
left join stats_wide sw      on p.pokemon_id = sw.pokemon_id
left join stat_totals st     on p.pokemon_id = st.pokemon_id
left join types_agg ty       on p.pokemon_id = ty.pokemon_id
left join abilities_agg ab   on p.pokemon_id = ab.pokemon_id
left join forms_agg fo       on p.pokemon_id = fo.pokemon_id
