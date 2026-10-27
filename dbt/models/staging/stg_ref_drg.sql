select
    {{ clean_string('drg_code') }}                        as drg_code,
    {{ clean_string('description') }}                     as drg_description,
    try_to_decimal({{ clean_string('relative_weight') }}, 6, 4)    as relative_weight,
    try_to_decimal({{ clean_string('geometric_mean_los') }}, 6, 2) as geometric_mean_los,
    try_to_boolean({{ clean_string('is_surgical') }})     as is_surgical
from {{ source('raw', 'ref_drg') }}
