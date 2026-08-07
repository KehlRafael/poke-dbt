{% macro pivot_by_slot(agg, slot_column, value_column, slot_labels) %}
{#
    Generates one aggregated CASE WHEN expression per slot, for pivoting a
    long-format relation into named columns by a known, static slot number
    (e.g. pokemon_types: type_slot, type_name -> primary_type, secondary_type).

    Unlike pivot_long_to_wide, which resolves pivot columns dynamically at COMPILE
    time via run_query against a lookup table, this macro takes the slot -> column
    name mapping directly as a Jinja dict - no lookup query needed, since the set
    of slots (e.g. primary/secondary type, ability 1/2/hidden) is fixed and known
    upfront. Caller wraps the output in their own select/group by.

    Args:
        agg:          aggregate function to apply, e.g. 'max'
        slot_column:  column holding the slot number, e.g. 'type_slot'
        value_column: column holding the value to aggregate, e.g. 'type_name'
        slot_labels:  dict mapping slot number -> output column name,
                      e.g. {1: 'primary_type', 2: 'secondary_type'}
#}
{% for slot, label in slot_labels.items() %}
{{ agg }}(case when {{ slot_column }} = {{ slot }} then {{ value_column }} end) as {{ label }}
{{- "," if not loop.last }}
{% endfor %}
{% endmacro %}
