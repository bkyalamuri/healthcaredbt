-- One row per NPI per version. valid_from / valid_to let you pick the record in force on a service date.
select
    {{ clean_string('npi') }}                     as npi,
    {{ clean_string('tax_id') }}                  as tax_id,
    {{ clean_string('provider_name') }}           as provider_name,
    {{ clean_string('provider_type') }}           as provider_type,
    {{ clean_string('specialty_code') }}          as specialty_code,
    {{ clean_string('specialty_desc') }}          as specialty_desc,
    {{ clean_string('address_line_1') }}          as address_line_1,
    {{ clean_string('city') }}                    as city,
    {{ clean_string('county') }}                  as county,
    upper({{ clean_string('state') }})            as state,
    {{ clean_string('zip') }}                     as zip,
    lower({{ clean_string('network_status') }})   as network_status,
    {{ parse_date('effective_date') }}            as valid_from,
    {{ parse_date('termination_date') }}          as valid_to,
    _source_system                                as source_system,
    try_to_timestamp(_extract_ts)                 as extracted_at
from {{ source('raw', 'providers') }}
