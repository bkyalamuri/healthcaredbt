select
    lpad({{ clean_string('pos_code') }}, 2, '0') as place_of_service_code,
    {{ clean_string('description') }}            as place_of_service_description
from {{ source('raw', 'ref_place_of_service') }}
