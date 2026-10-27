{{ config(enabled=false) }}
-- AE-108 · dim_provider
-- One row per NPI per version (valid_from / valid_to), so claims can join to the record in force on the service date.
--
-- Build from: stg_providers
-- Hint: Add a dbt_valid-style is_current flag.
-- Hint: Test: no two versions of one NPI overlap.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
