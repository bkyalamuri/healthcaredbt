-- Every chain that wasn't voided appears in fct_medical_claims exactly once.
with expected as (
    select distinct root_claim_id
    from {{ ref('int_medical_claim_chains') }}
    where not is_voided_chain
)
select e.root_claim_id
from expected e
left join {{ ref('fct_medical_claims') }} f on e.root_claim_id = f.root_claim_id
where f.root_claim_id is null
