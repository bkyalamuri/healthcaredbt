{{ config(enabled=false) }}
-- AE-106 · mart_quality_hba1c
-- HbA1c testing rate for diabetics by measurement year, LOB, plan and PCP. Simplified, not certified HEDIS.
--
-- Build from: fct_medical_claims, fct_medical_claim_lines, fct_pharmacy_claims, int_eligibility_spans
-- Hint: Denominator: age 18-75, continuously enrolled (one gap of up to 45 days), 2+ diabetes dx or 1 diabetes drug fill.
-- Hint: Numerator: CPT 83036 or 83037 in the year.
-- Hint: Continuous enrollment is the hard part; build an int_ model for it.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
