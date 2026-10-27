{{ config(enabled=false) }}
-- AE-107 · fct_pharmacy_claims
-- One row per fill net of reversals. Rejected transactions excluded.
--
-- Build from: stg_pharmacy_claims, stg_ref_ndc_drugs
-- Hint: A reversal points at its original via reversal_of_rx_claim_id; a reversed fill nets to zero.
-- Hint: Decide: drop reversed fills, or keep them with is_reversed? Write the choice down.
--
-- TODO: replace this stub, delete the config line above, and add the model to _marts.yml with tests.
select 1 as todo
