-- A voided chain must not contribute to the claim of record.
select f.claim_id
from {{ ref('fct_medical_claims') }} f
inner join {{ ref('int_medical_claim_chains') }} c on f.claim_id = c.claim_id
where c.is_voided_chain or not c.is_final_version
