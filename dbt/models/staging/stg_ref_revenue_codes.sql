select
    lpad({{ clean_string('revenue_code') }}, 4, '0') as revenue_code,
    {{ clean_string('description') }}                as revenue_description
from {{ source('raw', 'ref_revenue_codes') }}
