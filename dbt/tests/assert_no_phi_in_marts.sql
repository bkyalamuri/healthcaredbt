-- Compliance: outside the care-management outreach list, marts expose no direct identifiers.
select table_name, column_name
from {{ target.database }}.information_schema.columns
where table_schema = upper('{{ target.schema }}_marts')
  and table_name <> 'MART_CARE_MGMT_OUTREACH'
  and lower(column_name) in ('ssn', 'member_id', 'first_name', 'last_name', 'date_of_birth', 'dob',
                             'phone', 'email', 'address_line_1')
