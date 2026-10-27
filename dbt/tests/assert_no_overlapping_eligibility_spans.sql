-- After cleanup, a member can't be covered by two spans on the same day.
select a.member_id, a.eligibility_span_id, b.eligibility_span_id as overlapping_span_id
from {{ ref('int_eligibility_spans') }} a
inner join {{ ref('int_eligibility_spans') }} b
    on a.member_id = b.member_id
   and a.eligibility_span_id < b.eligibility_span_id
   and a.effective_date <= coalesce(b.termination_date, '9999-12-31'::date)
   and b.effective_date <= coalesce(a.termination_date, '9999-12-31'::date)
