-- One row per member coverage span with overlaps removed.
-- Retro-enrollment rows sometimes overlap an existing span. When two spans overlap,
-- the earlier one is cut off the day before the later one starts, so each day maps to one span.
with spans as (
    select distinct
        member_id,
        plan_id,
        line_of_business,
        effective_date,
        termination_date,
        pcp_npi,
        coverage_tier
    from {{ ref('stg_eligibility') }}
    where member_id is not null
      and effective_date is not null
),

ordered as (
    select
        *,
        lead(effective_date) over (
            partition by member_id
            order by effective_date, coalesce(termination_date, '9999-12-31'::date) desc
        ) as next_effective_date
    from spans
),

trimmed as (
    select
        member_id,
        plan_id,
        line_of_business,
        effective_date,
        case
            when next_effective_date is not null
             and next_effective_date <= coalesce(termination_date, '9999-12-31'::date)
                then dateadd(day, -1, next_effective_date)
            else termination_date
        end as termination_date,
        pcp_npi,
        coverage_tier,
        next_effective_date is not null
            and next_effective_date <= coalesce(termination_date, '9999-12-31'::date) as was_trimmed
    from ordered
)

select
    {{ dbt_utils.generate_surrogate_key(['member_id', 'effective_date', 'plan_id']) }} as eligibility_span_id,
    *,
    termination_date is null as is_open_span
from trimmed
-- a span fully covered by a later one collapses to nothing; drop it
where termination_date is null or termination_date >= effective_date
