# Pacific Crest Health data generator

Seeded Python generator for synthetic payer data. All people, NPIs, SSNs and NDCs are fake: SSNs start with 9 (never issued), NDC labeler codes start with 7, phone numbers use 555, emails use example.com.

```bash
pip install -r requirements.txt
python generate.py --scale 0.1 --seed 42 --out ../data   # ~800k rows, ~1 minute
python generate.py --scale 1.0 --seed 42 --out ../data   # ~8M rows, ~10 minutes
```

Same seed + scale always produces the same files. `data/manifest.json` lists row counts, file names, and the exact count of every injected problem.

## Business context

- Lines of business: Medicaid ~55%, Commercial ~35%, Medicare Advantage ~10% of members
- Coverage window: 2024-01-01 to 2026-06-30. Extract date: 2026-07-31, so recent months are incomplete (claims not yet received are absent, as in real life)
- Members in CA, NV, AZ; chronic cohorts (diabetes, hypertension, asthma, CHF) carry consistent ICD-10 codes and matching maintenance drugs
- Right-skewed cost: a small share of members (inpatient stays, oncology infusions, specialty biologics) drives a large share of spend
- Respiratory ER visits rise November through February

## Tables

| Table | Source system | Grain | Format |
| --- | --- | --- | --- |
| members | FACETS, LEGACY_MMIS, ENROLL_PORTAL | One row per member | CSV |
| eligibility | FACETS | One row per coverage span | CSV |
| plans | PRODUCT_CONFIG | One row per plan per benefit year | CSV |
| providers | CREDENTIALING | One row per NPI per change | CSV |
| medical_claims_header | CLAIMS_ADJ | One row per claim version | CSV |
| medical_claims_line | CLAIMS_ADJ | One row per claim line | CSV |
| pharmacy_claims | PBM | One row per fill, rejection or reversal | JSON lines |
| prior_authorizations | UM_SYS | One row per auth request | CSV |
| ref_icd10_dx, ref_cpt_hcpcs, ref_revenue_codes, ref_drg, ref_ndc_drugs, ref_place_of_service, ref_denial_reasons | REFERENCE | One row per code | CSV |

Reference tables are a curated subset of real code sets (~70 dx codes, ~75 procedure codes), not the full lists.

Every file carries `_source_system`, `_extract_ts` and `_file_name`. Files are gzip, ~250k rows each. Claim and line files named `*_resend_*` are a re-sent extract.

## Injected data-quality problems

Rates are approximate; `manifest.json` has the exact counts for your run.

| Problem | Where | Rate |
| --- | --- | --- |
| Exact duplicate rows from a re-sent extract | claim headers + their lines | ~0.5% of headers |
| Replacements (frequency 7) pointing at the previous version, sometimes twice | claim headers | ~6% of claims |
| Voids (frequency 8) with negative amounts; the whole chain should drop out | claim headers | ~1% of claims |
| Pharmacy reversals with negative amounts referencing the original fill | pharmacy | ~3% of paid fills |
| Late-arriving claims: most within 60 days, a tail up to 18 months | claim headers | ~3% over 120 days |
| Mixed date formats: YYYY-MM-DD, MM/DD/YYYY, YYYYMMDD | members.dob (~25%), claim service and received dates (~1%) | |
| Diagnosis codes without the decimal, lowercase, or with trailing spaces | all dx columns | ~25% / 3% / 2% |
| Reference dx codes stored without the decimal (CMS style) | ref_icd10_dx | all rows |
| Orphan member IDs | claim headers | ~0.3% |
| Orphan NPIs | claim headers | ~0.5% |
| Service dates outside the member's coverage (about half denied CO-27, half paid by mistake) | claim headers | ~1% |
| Header paid doesn't equal the sum of line paid | claim headers | ~0.5% |
| 'NULL', 'N/A' and '' strings instead of real nulls | phone, email, rendering_npi | ~1-2% |
| Gender coded M/F/U, 1/2/9, Male/Female by source system | members | |
| Multiple rows per NPI over time (address or network change) | providers | ~13% of NPIs |
| Overlapping retro-enrollment spans | eligibility | ~0.5% of members |
| Open spans as NULL or 9999-12-31 | eligibility | ~30% of open spans use the sentinel |
| Hyphenated NDCs (5-4-2) | pharmacy | ~5% |
| Future-dated service dates | claim headers | ~0.02% |
| Negative allowed amounts that are errors, not reversals | claim headers | ~0.02% |
| Prior auths that never became claims (denied requests) | prior_authorizations | ~13% |
