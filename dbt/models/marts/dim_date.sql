{{ config(enabled=false) }}
-- Dimensions · dim_date
-- One row per calendar day for the coverage window.
--
-- Hint: Look at dbt_utils.date_spine.
-- Hint: Include month_start, year, and a is_flu_season flag (Nov-Feb) for AE-104.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
