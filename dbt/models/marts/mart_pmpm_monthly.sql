{{ config(enabled=false) }}
-- AE-102 · mart_pmpm_monthly
-- Paid PMPM by line of business, plan and month, split by category of service (inpatient, outpatient, ER, professional, pharmacy).
--
-- Build from: fct_member_months, fct_medical_claims, fct_pharmacy_claims
-- Hint: PMPM = paid / member months. Aggregate each side to month first, then join; joining claims to member months directly fans out.
-- Hint: Singular test: total paid here = total paid in the two facts.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
