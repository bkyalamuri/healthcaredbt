{#
  Reusable cleanup rules for raw source columns. Every staging model uses these,
  so a rule changes in one place.
#}

{# Trim, and turn the placeholder strings source systems send for "no value" into a real NULL. #}
{% macro clean_string(col) -%}
    nullif(nullif(nullif(nullif(trim({{ col }}), ''), 'NULL'), 'N/A'), 'null')
{%- endmacro %}


{# Sources send dates as YYYY-MM-DD, MM/DD/YYYY or YYYYMMDD. Try each format in turn. #}
{% macro parse_date(col) -%}
    coalesce(
        try_to_date({{ clean_string(col) }}, 'YYYY-MM-DD'),
        try_to_date({{ clean_string(col) }}, 'MM/DD/YYYY'),
        try_to_date({{ clean_string(col) }}, 'YYYYMMDD')
    )
{%- endmacro %}


{# ICD-10 codes arrive as E11.9, E119, e11.9 or with trailing spaces. Store the decimal-free uppercase form used by the reference table. #}
{% macro clean_dx_code(col) -%}
    nullif(upper(replace(trim({{ col }}), '.', '')), '')
{%- endmacro %}


{# FACETS sends M/F/U, the legacy Medicaid system 1/2/9, the enrollment portal Male/Female. #}
{% macro standardize_gender(col) -%}
    case
        when upper(trim({{ col }})) in ('M', 'MALE', '1') then 'M'
        when upper(trim({{ col }})) in ('F', 'FEMALE', '2') then 'F'
        else 'U'
    end
{%- endmacro %}


{# Money arrives as text; cast safely so one bad value doesn't fail the model. #}
{% macro to_amount(col) -%}
    try_to_decimal({{ clean_string(col) }}, 14, 2)
{%- endmacro %}


{# The only member identifier allowed in marts outside the care-management list (Compliance rule). #}
{% macro member_sk(col) -%}
    md5(cast({{ col }} as varchar))
{%- endmacro %}
