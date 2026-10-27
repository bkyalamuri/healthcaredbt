select
    replace({{ clean_string('ndc') }}, '-', '')   as ndc,
    {{ clean_string('drug_name') }}               as drug_name,
    {{ clean_string('generic_flag') }} = 'Y'      as is_generic,
    {{ clean_string('specialty_flag') }} = 'Y'    as is_specialty,
    {{ clean_string('therapeutic_class') }}       as therapeutic_class
from {{ source('raw', 'ref_ndc_drugs') }}
