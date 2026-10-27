select
    {{ clean_dx_code('dx_code') }}            as dx_code,
    {{ clean_string('dx_description') }}      as dx_description,
    {{ clean_string('chronic_condition') }}   as chronic_condition
from {{ source('raw', 'ref_icd10_dx') }}
