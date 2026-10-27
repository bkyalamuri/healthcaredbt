select
    {{ clean_string('denial_reason_code') }} as denial_reason_code,
    {{ clean_string('description') }}        as denial_reason_description,
    {{ clean_string('category') }}           as denial_category
from {{ source('raw', 'ref_denial_reasons') }}
