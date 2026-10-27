{{ config(enabled=false) }}
-- Dimensions · dim_member
-- One row per member_sk. Hashed key plus non-PHI attributes: gender, age band, state, county, preferred language, current LOB and plan.
--
-- Build from: stg_members, int_eligibility_spans
-- Hint: Use the member_sk() macro so keys join to fct_medical_claims.
-- Hint: Age band from date_of_birth as of the coverage end date (var).
-- Hint: Current plan = the open span, else the most recent one.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
