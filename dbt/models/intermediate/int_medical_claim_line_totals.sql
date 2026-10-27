-- One row per claim version: line totals and the line-level facts headers don't carry.
select
    claim_id,
    count(*)                                                  as line_count,
    sum(line_billed_amt)                                      as line_billed_amt,
    sum(line_allowed_amt)                                     as line_allowed_amt,
    sum(line_paid_amt)                                        as line_paid_amt,
    max(iff(revenue_code between '0450' and '0459', 1, 0)) = 1 as has_er_revenue_code
from {{ ref('stg_medical_claims_line') }}
group by claim_id
