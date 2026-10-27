-- Every claim chain must resolve to exactly one final version.
select root_claim_id, count_if(is_final_version) as final_versions
from {{ ref('int_medical_claim_chains') }}
group by root_claim_id
having count_if(is_final_version) <> 1
