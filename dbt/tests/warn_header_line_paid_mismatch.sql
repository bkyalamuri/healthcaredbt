-- Known source issue (~0.5% of claims): header paid doesn't equal the sum of line paid.
-- Severity warn so the build passes while Claims Operations works the list.
{{ config(severity='warn') }}
select claim_id, header_paid_amt, paid_amt
from {{ ref('fct_medical_claims') }}
where has_header_line_mismatch
