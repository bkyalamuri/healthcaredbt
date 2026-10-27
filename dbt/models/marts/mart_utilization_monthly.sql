{{ config(enabled=false) }}
-- AE-104 · mart_utilization_monthly
-- Inpatient admits, ER visits and advanced imaging per 1,000 members, by month and LOB.
--
-- Build from: fct_medical_claims, fct_medical_claim_lines, fct_member_months
-- Hint: Admits: one per inpatient facility stay (admit date), not per claim.
-- Hint: ER visit: revenue code 0450-0459 or POS 23; one per member per day.
-- Hint: Per 1,000 = events / member months x 12,000.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
