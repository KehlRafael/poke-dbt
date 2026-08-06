{% macro stat_tier(stat_total_column) %}
    case
        when {{ stat_total_column }} >= 580 then 'S - Top tier'
        when {{ stat_total_column }} >= 500 then 'A - Strong'
        when {{ stat_total_column }} >= 420 then 'B - Balanced'
        when {{ stat_total_column }} >= 320 then 'C - Below average'
        else 'D - Weak'
    end
{% endmacro %}
