-- One row per plan per benefit year.
select
    {{ clean_string('plan_id') }}                  as plan_id,
    {{ clean_string('plan_name') }}                as plan_name,
    {{ clean_string('lob') }}                      as line_of_business,
    {{ clean_string('metal_tier') }}               as metal_tier,
    upper({{ clean_string('state') }})             as state,
    try_to_number({{ clean_string('deductible') }}) as deductible_amt,
    try_to_number({{ clean_string('oop_max') }})   as oop_max_amt,
    try_to_number({{ clean_string('effective_year') }}) as benefit_year
from {{ source('raw', 'plans') }}
