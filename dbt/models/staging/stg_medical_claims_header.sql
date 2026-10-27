-- One row per claim version (originals, replacements and voids).
-- Exact duplicates from re-sent extract files are removed here; chain resolution happens in intermediate.
with source as (
    select * from {{ source('raw', 'medical_claims_header') }}
),

deduplicated as (
    select *
    from source
    -- a re-sent file repeats rows we already have; keep the copy from the earliest extract
    qualify row_number() over (partition by claim_id order by _extract_ts, _file_name) = 1
),

renamed as (
    select
        {{ clean_string('claim_id') }}                         as claim_id,
        {{ clean_string('claim_frequency_code') }}             as claim_frequency_code,
        {{ clean_string('original_claim_id') }}                as previous_claim_id,
        {{ clean_string('member_id') }}                        as member_id,
        {{ clean_string('billing_npi') }}                      as billing_npi,
        {{ clean_string('rendering_npi') }}                    as rendering_npi,
        {{ clean_string('claim_type') }}                       as claim_type,
        {{ clean_string('bill_type') }}                        as bill_type,
        lpad({{ clean_string('place_of_service') }}, 2, '0')   as place_of_service_code,
        {{ parse_date('admit_date') }}                         as admit_date,
        {{ parse_date('discharge_date') }}                     as discharge_date,
        {{ parse_date('service_from_date') }}                  as service_from_date,
        {{ parse_date('service_to_date') }}                    as service_to_date,
        {{ parse_date('received_date') }}                      as received_date,
        {{ parse_date('adjudicated_date') }}                   as adjudicated_date,
        {{ parse_date('paid_date') }}                          as paid_date,
        lower({{ clean_string('claim_status') }})              as claim_status,
        {{ clean_string('denial_reason_code') }}               as denial_reason_code,
        {{ to_amount('total_billed_amt') }}                    as header_billed_amt,
        {{ to_amount('total_allowed_amt') }}                   as header_allowed_amt,
        {{ to_amount('total_paid_amt') }}                      as header_paid_amt,
        {{ to_amount('member_responsibility_amt') }}           as header_member_resp_amt,
        {{ clean_dx_code('primary_dx_code') }}                 as primary_dx_code,
        {%- for i in range(2, 13) %}
        {{ clean_dx_code('dx_code_' ~ i) }}                    as dx_code_{{ i }},
        {%- endfor %}
        {{ clean_string('drg_code') }}                         as drg_code,
        _source_system                                         as source_system,
        try_to_timestamp(_extract_ts)                          as extracted_at,
        _file_name                                             as source_file_name
    from deduplicated
)

select * from renamed
