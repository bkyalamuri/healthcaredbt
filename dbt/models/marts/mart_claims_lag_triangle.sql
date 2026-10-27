{{ config(enabled=false) }}
-- AE-103 · mart_claims_lag_triangle
-- Paid amount by incurred month x months from incurred to paid (0-18), plus a completion factor per incurred month.
--
-- Build from: fct_medical_claims
-- Hint: Incurred = service_from month; paid lag = months between incurred_month and paid_date.
-- Hint: Completion factor: cumulative paid at lag k / cumulative paid at the max lag, averaged over mature months.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
