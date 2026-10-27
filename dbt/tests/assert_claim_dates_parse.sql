-- Any raw date that arrived but didn't parse means a new source format to handle in parse_date().
select claim_id, service_from_date, received_date
from {{ source('raw', 'medical_claims_header') }}
where (nullif(trim(service_from_date), '') is not null and {{ parse_date('service_from_date') }} is null)
   or (nullif(trim(received_date), '') is not null and {{ parse_date('received_date') }} is null)
