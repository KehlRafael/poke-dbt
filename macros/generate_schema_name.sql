{#
    dbt's default generate_schema_name concatenates target.schema with the
    custom schema (e.g. 'pokedex_stg'). This project wants custom schemas
    (raw, stg) used literally, so this overrides that default.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}

        {{ default_schema }}

    {%- else -%}

        {{ custom_schema_name | trim }}

    {%- endif -%}

{%- endmacro %}
