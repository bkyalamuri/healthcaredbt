-- One row per authorization request.
select
    {{ clean_string('auth_id') }}               as auth_id,
    {{ clean_string('member_id') }}             as member_id,
    {{ clean_string('requesting_npi') }}        as requesting_npi,
    {{ clean_string('service_type') }}          as service_type,
    upper({{ clean_string('procedure_code') }}) as procedure_code,
    {{ parse_date('request_date') }}            as request_date,
    {{ parse_date('decision_date') }}           as decision_date,
    lower({{ clean_string('decision') }})       as decision,
    lower({{ clean_string('urgency') }})        as urgency,
    try_to_timestamp(_extract_ts)               as extracted_at
from {{ source('raw', 'prior_authorizations') }}
