{{ config(enabled=false) }}
-- AE-102 · fct_member_months
-- One row per member per month covered. A member counts in a month if covered on the 15th (write this rule in the YAML).
--
-- Build from: int_eligibility_spans, dim_date
-- Hint: Join spans to month starts where the 15th falls inside the span.
-- Hint: Carry plan_id and line_of_business from the span.
-- Hint: Test: unique member_sk + month.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
