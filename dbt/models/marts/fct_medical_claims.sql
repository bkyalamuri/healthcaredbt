-- AE-101 · Claim of record. One row per final claim version of every chain that wasn't voided.
-- Amounts of record come from the service lines; the header paid amount is kept for reconciliation.
-- Data problems are flagged, not dropped, so Claims Operations can work them.
{{ config(materialized='table') }}

with chains as (
    select * from {{ ref('int_medical_claim_chains') }}
    where is_final_version and not is_voided_chain
),

headers as (
    select * from {{ ref('stg_medical_claims_header') }}
),

line_totals as (
    select * from {{ ref('int_medical_claim_line_totals') }}
),

members as (
    select distinct member_id from {{ ref('stg_members') }}
),

providers as (
    select distinct npi from {{ ref('stg_providers') }}
),

eligibility as (
    select * from {{ ref('int_eligibility_spans') }}
),

claims as (
    select
        h.claim_id,
        c.root_claim_id,
        c.versions_in_chain,
        c.versions_in_chain > 1                                  as was_adjusted,
        {{ member_sk('h.member_id') }}                           as member_sk,
        h.billing_npi,
        h.rendering_npi,
        h.claim_type,
        h.bill_type,
        h.place_of_service_code,
        case
            when h.claim_type = 'institutional' and h.bill_type like '011%' then 'Inpatient Facility'
            when h.claim_type = 'institutional' and lt.has_er_revenue_code then 'Emergency Facility'
            when h.claim_type = 'institutional' then 'Outpatient Facility'
            when h.place_of_service_code = '23' then 'Emergency Professional'
            else 'Professional'
        end                                                      as category_of_service,
        h.admit_date,
        h.discharge_date,
        h.service_from_date,
        h.service_to_date,
        date_trunc('month', h.service_from_date)                 as incurred_month,
        h.received_date,
        h.adjudicated_date,
        h.paid_date,
        datediff(day, h.service_to_date, h.received_date)        as days_service_to_received,
        h.claim_status,
        h.denial_reason_code,
        lt.line_count,
        lt.line_billed_amt                                       as billed_amt,
        lt.line_allowed_amt                                      as allowed_amt,
        lt.line_paid_amt                                         as paid_amt,
        h.header_member_resp_amt                                 as member_responsibility_amt,
        h.header_paid_amt,
        h.primary_dx_code,
        h.dx_code_2, h.dx_code_3, h.dx_code_4, h.dx_code_5, h.dx_code_6, h.dx_code_7,
        h.dx_code_8, h.dx_code_9, h.dx_code_10, h.dx_code_11, h.dx_code_12,
        h.drg_code,
        e.plan_id,
        e.line_of_business,

        -- data-quality flags
        m.member_id is null                                      as is_orphan_member,
        (h.billing_npi is not null and bp.npi is null)
            or (h.rendering_npi is not null and rp.npi is null)  as is_orphan_provider,
        e.member_id is null                                      as is_outside_eligibility,
        abs(coalesce(h.header_paid_amt, 0) - coalesce(lt.line_paid_amt, 0)) > 0.01
                                                                 as has_header_line_mismatch,
        h.service_from_date > '{{ var("extract_date") }}'::date  as is_future_service_date,
        h.header_allowed_amt < 0                                 as has_negative_allowed,
        h.service_from_date is null                              as is_unparseable_service_date
    from chains c
    inner join headers h on c.claim_id = h.claim_id
    left join line_totals lt on h.claim_id = lt.claim_id
    left join members m on h.member_id = m.member_id
    left join providers bp on h.billing_npi = bp.npi
    left join providers rp on h.rendering_npi = rp.npi
    left join eligibility e
        on h.member_id = e.member_id
       and h.service_from_date between e.effective_date and coalesce(e.termination_date, '9999-12-31'::date)
)

select
    *,
    is_orphan_member or is_orphan_provider or is_outside_eligibility or has_header_line_mismatch
        or is_future_service_date or has_negative_allowed or is_unparseable_service_date as has_any_dq_issue
from claims
