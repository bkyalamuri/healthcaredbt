-- One row per coverage span as delivered. Overlapping spans are resolved in int_eligibility_spans.
with source as (
    select * from {{ source('raw', 'eligibility') }}
),

renamed as (
    select
        {{ clean_string('member_id') }}                       as member_id,
        {{ clean_string('plan_id') }}                         as plan_id,
        {{ clean_string('lob') }}                             as line_of_business,
        {{ parse_date('effective_date') }}                    as effective_date,
        -- open spans arrive as NULL or the 9999-12-31 sentinel; standardize to NULL
        case
            when {{ clean_string('termination_date') }} = '9999-12-31' then null
            else {{ parse_date('termination_date') }}
        end                                                   as termination_date,
        {{ clean_string('pcp_npi') }}                         as pcp_npi,
        {{ clean_string('coverage_tier') }}                   as coverage_tier,
        _source_system                                        as source_system,
        try_to_timestamp(_extract_ts)                         as extracted_at,
        _file_name                                            as source_file_name
    from source
)

select
    *,
    termination_date is null as is_open_span
from renamed
