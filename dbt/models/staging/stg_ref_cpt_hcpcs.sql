select
    upper({{ clean_string('procedure_code') }}) as procedure_code,
    {{ clean_string('description') }}           as procedure_description,
    {{ clean_string('category') }}              as procedure_category
from {{ source('raw', 'ref_cpt_hcpcs') }}
