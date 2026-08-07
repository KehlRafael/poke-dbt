with pokemon as (
    select * from {{ ref('stg_pokemon') }}
),

species as (
    select * from {{ ref('stg_pokemon_species') }}
),

stats_wide as (
    select * from {{ ref('int_pokemon_stats_pivoted') }}
),

types_joined as (
    select pt.pokemon_id, pt.type_slot, t.type_name
    from {{ ref('stg_pokemon_types') }} pt
    inner join {{ ref('stg_types') }} t on pt.type_id = t.type_id
),

types_agg as (
    select
        pokemon_id,
        {{ pivot_by_slot(
            agg='max',
            slot_column='type_slot',
            value_column='type_name',
            slot_labels={1: 'primary_type', 2: 'secondary_type'}
        ) }}
    from types_joined
    group by pokemon_id
),

abilities_joined as (
    select pa.pokemon_id, pa.ability_slot, a.ability_name
    from {{ ref('stg_pokemon_abilities') }} pa
    inner join {{ ref('stg_abilities') }} a on pa.ability_id = a.ability_id
),

abilities_agg as (
    select
        pokemon_id,
        {{ pivot_by_slot(
            agg='max',
            slot_column='ability_slot',
            value_column='ability_name',
            slot_labels={1: 'ability_1', 2: 'ability_2', 3: 'hidden_ability'}
        ) }}
    from abilities_joined
    group by pokemon_id
),

stat_totals as (
    select
        ps.pokemon_id,
        sum(ps.base_stat) as stat_total
    from {{ ref('stg_pokemon_stats') }} ps
    inner join {{ ref('stg_stats') }} sl on ps.stat_id = sl.stat_id
    where sl.stat_name in ('hp', 'attack', 'defense', 'special-attack', 'special-defense', 'speed')
    group by ps.pokemon_id
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
