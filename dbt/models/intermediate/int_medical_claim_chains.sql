-- One row per claim version, tied to the original claim that started its chain.
-- Replacements (frequency 7) and voids (frequency 8) point at the version they change,
-- so a chain can be several links long: original -> replacement -> replacement -> void.
with recursive headers as (
    select claim_id, previous_claim_id, claim_frequency_code, received_date, adjudicated_date
    from {{ ref('stg_medical_claims_header') }}
),

chain (claim_id, root_claim_id, chain_depth, is_orphan_adjustment) as (
    -- anchors: originals, plus adjustments whose previous version never arrived
    select
        h.claim_id,
        h.claim_id,
        0::int,
        h.previous_claim_id is not null
    from headers h
    left join headers p on h.previous_claim_id = p.claim_id
    where h.previous_claim_id is null
       or p.claim_id is null

    union all

    select
        h.claim_id,
        c.root_claim_id,
        (c.chain_depth + 1)::int,
        c.is_orphan_adjustment
    from headers h
    inner join chain c on h.previous_claim_id = c.claim_id
),

ranked as (
    select
        c.claim_id,
        c.root_claim_id,
        c.chain_depth,
        c.is_orphan_adjustment,
        h.claim_frequency_code,
        count(*) over (partition by c.root_claim_id) as versions_in_chain,
        row_number() over (
            partition by c.root_claim_id
            order by c.chain_depth desc, h.received_date desc, h.adjudicated_date desc nulls last, c.claim_id desc
        ) as version_rank
    from chain c
    inner join headers h on c.claim_id = h.claim_id
)

select
    claim_id,
    root_claim_id,
    chain_depth,
    versions_in_chain,
    is_orphan_adjustment,
    version_rank = 1 as is_final_version,
    -- the whole chain is voided when its latest version is a void
    max(case when version_rank = 1 and claim_frequency_code = '8' then 1 else 0 end)
        over (partition by root_claim_id) = 1 as is_voided_chain
from ranked
