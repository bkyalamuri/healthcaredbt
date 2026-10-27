-- One row per PBM transaction (fills, rejections and reversals), flattened from JSON.
-- Reversals still carry negative amounts here; netting them is part of AE-107.
with source as (
    select raw_record as r from {{ source('raw', 'pharmacy_claims') }}
)

select
    r:rx_claim_id::string                                   as rx_claim_id,
    r:member_id::string                                     as member_id,
    try_to_date(r:fill_date::string)                        as fill_date,
    try_to_timestamp(r:adjudicated_ts::string)              as adjudicated_at,
    r:pharmacy:npi::string                                  as pharmacy_npi,
    r:pharmacy:name::string                                 as pharmacy_name,
    r:pharmacy:chain::string                                as pharmacy_chain,
    r:prescriber_npi::string                                as prescriber_npi,
    -- NDCs arrive as 11 digits or hyphenated 5-4-2; store the 11-digit form
    replace(r:drug:ndc::string, '-', '')                    as ndc,
    r:drug:name::string                                     as drug_name,
    r:drug:generic_flag::string = 'Y'                       as is_generic,
    r:drug:specialty_flag::string = 'Y'                     as is_specialty,
    r:drug:therapeutic_class::string                        as therapeutic_class,
    r:quantity::number(12, 2)                               as quantity,
    r:days_supply::int                                      as days_supply,
    r:ingredient_cost::number(14, 2)                        as ingredient_cost_amt,
    r:dispensing_fee::number(14, 2)                         as dispensing_fee_amt,
    r:plan_paid::number(14, 2)                              as plan_paid_amt,
    r:member_copay::number(14, 2)                           as member_copay_amt,
    lower(r:claim_status::string)                           as claim_status,
    r:reversal_of_rx_claim_id::string                       as reversal_of_rx_claim_id,
    try_to_timestamp(r:_extract_ts::string)                 as extracted_at
from source
