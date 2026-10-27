{{ config(enabled=false) }}
-- AE-105 · mart_care_mgmt_outreach
-- One row per currently eligible member flagged high-cost (rolling-12 paid > $50k), frequent ER (4+ in 12 months), 30-day readmission, or chronic conditions. Name and phone allowed here only.
--
-- Build from: fct_medical_claims, stg_members, int_eligibility_spans, stg_ref_icd10_dx
-- Hint: Build int_ models for each flag first, then join.
-- Hint: Readmission: next admit within 30 days of a discharge, same member.
-- Hint: Chronic flags from any dx position joined to stg_ref_icd10_dx.chronic_condition.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
