-- AE-101 · Service lines for every claim in fct_medical_claims. One row per claim line.
{{ config(materialized='table') }}

select
    {{ dbt_utils.generate_surrogate_key(['l.claim_id', 'l.line_number']) }} as claim_line_id,
    l.claim_id,
    l.line_number,
    c.member_sk,
    c.category_of_service,
    c.claim_status,
    c.line_of_business,
    l.line_service_date,
    l.procedure_code,
    p.procedure_category,
    l.modifier_1,
    l.modifier_2,
    l.revenue_code,
    l.units,
    l.line_billed_amt,
    l.line_allowed_amt,
    l.line_paid_amt
from {{ ref('stg_medical_claims_line') }} l
inner join {{ ref('fct_medical_claims') }} c on l.claim_id = c.claim_id
left join {{ ref('stg_ref_cpt_hcpcs') }} p on l.procedure_code = p.procedure_code
