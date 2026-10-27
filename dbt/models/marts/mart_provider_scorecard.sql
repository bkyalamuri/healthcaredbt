{{ config(enabled=false) }}
-- AE-108 · mart_provider_scorecard
-- Per rendering provider: unique members, claims, paid, cost per unique member, denial rate; flag > 25% above specialty median with 50+ members.
--
-- Build from: fct_medical_claims, dim_provider
-- Hint: Join on rendering_npi and service date between valid_from and valid_to.
-- Hint: Snowflake has median() as a window function.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
