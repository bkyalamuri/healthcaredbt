-- One row per member. SSN is dropped here (Compliance rule) and never reaches downstream models.
with source as (
    select * from {{ source('raw', 'members') }}
),

renamed as (
    select
        {{ clean_string('member_id') }}                       as member_id,
        {{ clean_string('subscriber_id') }}                   as subscriber_id,
        {{ clean_string('relationship_code') }}               as relationship_code,
        case {{ clean_string('relationship_code') }}
            when '18' then 'Self'
            when '01' then 'Spouse'
            when '19' then 'Child'
            else 'Other'
        end                                                   as relationship,
        initcap({{ clean_string('first_name') }})             as first_name,
        initcap({{ clean_string('last_name') }})              as last_name,
        {{ parse_date('dob') }}                               as date_of_birth,
        {{ standardize_gender('gender') }}                    as gender,
        {{ clean_string('address_line_1') }}                  as address_line_1,
        {{ clean_string('city') }}                            as city,
        {{ clean_string('county') }}                          as county,
        upper({{ clean_string('state') }})                    as state,
        {{ clean_string('zip') }}                             as zip,
        -- keep digits only so (949) 555-0123, 949-555-0123 and 9495550123 match
        nullif(regexp_replace({{ clean_string('phone') }}, '[^0-9]', ''), '') as phone,
        lower({{ clean_string('email') }})                    as email,
        {{ clean_string('preferred_language') }}              as preferred_language,
        {{ clean_string('race_ethnicity_code') }}             as race_ethnicity_code,
        try_to_timestamp({{ clean_string('created_at') }})    as created_at,
        try_to_timestamp({{ clean_string('updated_at') }})    as updated_at,
        _source_system                                        as source_system,
        try_to_timestamp(_extract_ts)                         as extracted_at,
        _file_name                                            as source_file_name
    from source
)

select * from renamed
