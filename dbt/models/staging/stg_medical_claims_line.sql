-- One row per claim line. Duplicate lines from re-sent extract files are removed here.
with source as (
    select * from {{ source('raw', 'medical_claims_line') }}
),

deduplicated as (
    select *
    from source
    qualify row_number() over (partition by claim_id, line_number order by _extract_ts, _file_name) = 1
)

select
    {{ clean_string('claim_id') }}                          as claim_id,
    try_to_number({{ clean_string('line_number') }})        as line_number,
    upper({{ clean_string('procedure_code') }})             as procedure_code,
    upper({{ clean_string('modifier_1') }})                 as modifier_1,
    upper({{ clean_string('modifier_2') }})                 as modifier_2,
    lpad({{ clean_string('revenue_code') }}, 4, '0')        as revenue_code,
    try_to_decimal({{ clean_string('units') }}, 10, 2)      as units,
    {{ to_amount('line_billed_amt') }}                      as line_billed_amt,
    {{ to_amount('line_allowed_amt') }}                     as line_allowed_amt,
    {{ to_amount('line_paid_amt') }}                        as line_paid_amt,
    {{ parse_date('line_service_date') }}                   as line_service_date,
    try_to_timestamp(_extract_ts)                           as extracted_at
from deduplicated
