{% macro pivot_long_to_wide(relation, group_by_column, pivot_id_column, value_column, lookup_relation, lookup_id_column, lookup_name_column, agg='max', prefix='') %}
{#
    Pivots a long-format table (e.g. stg_pokemon_stats: pokemon_id, stat_id, base_stat)
    into wide format, generating one column per distinct value found in a lookup table
    (e.g. stg_stats: stat_id, stat_name).

    This is resolved at COMPILE time: the lookup table is queried via run_query so the
    generated SQL contains one literal CASE WHEN per row, in the same style dbt_utils.pivot
    uses under the hood - written out here so the Jinja loop itself is visible on slides.

    Args:
        relation:            the long-format relation to pivot, e.g. ref('stg_pokemon_stats')
        group_by_column:     column to group by, e.g. 'pokemon_id'
        pivot_id_column:     column holding the id to pivot on, e.g. 'stat_id'
        value_column:        column holding the value to aggregate, e.g. 'base_stat'
        lookup_relation:     lookup table mapping id -> readable name, e.g. ref('stg_stats')
        lookup_id_column:    id column in the lookup table, e.g. 'stat_id'
        lookup_name_column:  name column in the lookup table, e.g. 'stat_name'
        agg:                 aggregate function to apply, default 'max'
        prefix:              optional prefix for generated column names
#}

{% set lookup_query %}
    select distinct {{ lookup_id_column }}, {{ lookup_name_column }}
    from {{ lookup_relation }}
    order by {{ lookup_id_column }}
{% endset %}

{% set lookup_results = run_query(lookup_query) %}

{% if execute %}
    {% set pivot_values = lookup_results.rows %}
{% else %}
    {% set pivot_values = [] %}
{% endif %}

select
    {{ group_by_column }},
    {% for row in pivot_values %}
    {{ agg }}(
        case when {{ pivot_id_column }} = {{ row[0] }} then {{ value_column }} end
    ) as {{ prefix }}{{ row[1] | replace('-', '_') }}
    {{- "," if not loop.last }}
    {% endfor %}
from {{ relation }}
group by {{ group_by_column }}

{% endmacro %}
