"""Pacific Crest Health synthetic payer data generator.

Usage:
    python generate.py --scale 0.1 --seed 42 --out ../data
"""
import argparse
import gzip
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

import entities as ent
import medical as med
import pharmacy as rx
from reference import DX, PROC, REV, DRG, POS, DENIALS, DRUGS

EXTRACT_TS = "2026-07-31 23:45:00"
RESEND_TS = "2026-08-01 02:10:00"


class TableWriter:
    """Buffers rows and writes gzip files of ~rows_per_file rows into <out>/<table>/."""

    def __init__(self, out, table, source, fmt="csv", rows_per_file=250_000, tag="", extract_ts=EXTRACT_TS):
        self.dir = Path(out) / table
        self.dir.mkdir(parents=True, exist_ok=True)
        self.table, self.source, self.fmt, self.rpf, self.tag, self.ts = table, source, fmt, rows_per_file, tag, extract_ts
        self.buf, self.nbuf, self.seq, self.total = [], 0, 0, 0
        self.files = []

    def add(self, data):
        if data is None or len(data) == 0:
            return
        self.buf.append(data)
        self.nbuf += len(data)
        while self.nbuf >= self.rpf:
            self._flush(self.rpf)

    def close(self):
        if self.nbuf:
            self._flush(self.nbuf)
        return self

    def _take(self, k):
        out, need = [], k
        while need:
            head = self.buf[0]
            if len(head) <= need:
                out.append(self.buf.pop(0))
                need -= len(head)
            else:
                out.append(head[:need])
                self.buf[0] = head[need:]
                need = 0
        self.nbuf -= k
        return out

    def _flush(self, k):
        parts = self._take(k)
        self.seq += 1
        stamp = self.ts[:10].replace("-", "")
        ext = "csv.gz" if self.fmt == "csv" else "json.gz"
        name = f"{self.table}_{self.tag}{stamp}_{self.seq:03d}.{ext}"
        path = self.dir / name
        if self.fmt == "csv":
            df = pd.concat(parts, ignore_index=True)
            if "_source_system" not in df.columns:
                df["_source_system"] = self.source
            df["_extract_ts"] = self.ts
            df["_file_name"] = name
            df.to_csv(path, index=False, compression="gzip")
        else:
            with gzip.open(path, "wt") as f:
                for part in parts:
                    for r in part:
                        r = {**r, "_source_system": self.source, "_extract_ts": self.ts, "_file_name": name}
                        f.write(json.dumps(r) + "\n")
        self.total += k
        self.files.append(name)


def iso(s):
    s = pd.to_datetime(pd.Series(s))
    return s.dt.strftime("%Y-%m-%d").where(s.notna(), None).values


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="../data")
    ap.add_argument("--chunk-members", type=int, default=20_000)
    args = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(args.seed)
    fake = Faker("en_US")
    Faker.seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stats = Counter()
    counters = {"claim": 1_000_000, "rx": 5_000_000, "auth": 100_000}
    log = lambda m: print(f"[{time.time() - t0:7.1f}s] {m}", flush=True)

    n_members = max(1000, int(200_000 * args.scale))
    n_prov = max(1500, int(30_000 * args.scale))

    # ---- reference tables
    refs = {
        "ref_icd10_dx": pd.DataFrame([{"dx_code": k.replace(".", ""), "dx_description": v[0], "chronic_condition": v[1]}
                                      for k, v in DX.items()]),
        "ref_cpt_hcpcs": pd.DataFrame([{"procedure_code": k, "description": v[0], "category": v[1]} for k, v in PROC.items()]),
        "ref_revenue_codes": pd.DataFrame([{"revenue_code": k, "description": v[0]} for k, v in REV.items()]),
        "ref_drg": pd.DataFrame([{"drg_code": k, "description": v[0], "relative_weight": v[1], "geometric_mean_los": v[2],
                                  "is_surgical": v[3]} for k, v in DRG.items()]),
        "ref_ndc_drugs": pd.DataFrame([{"ndc": v[0], "drug_name": v[1], "generic_flag": v[2], "specialty_flag": v[3],
                                        "therapeutic_class": v[4]} for v in DRUGS.values()]),
        "ref_place_of_service": pd.DataFrame([{"pos_code": k, "description": v} for k, v in POS.items()]),
        "ref_denial_reasons": pd.DataFrame([{"denial_reason_code": k, "description": v[0], "category": v[1]}
                                            for k, v in DENIALS.items()]),
    }
    written = {}
    for name, df in refs.items():
        written[name] = TableWriter(out, name, "REFERENCE")
        written[name].add(df)
        written[name].close()

    # ---- plans, providers, members, eligibility
    plans = ent.build_plans_df(rng)
    w = TableWriter(out, "plans", "PRODUCT_CONFIG"); w.add(plans); written["plans"] = w.close()
    log("plans done")

    prov = ent.build_providers(rng, fake, n_prov)
    lut, oon = ent.provider_lookup(prov)
    praw = prov.drop(columns=["_group"]).copy()
    praw["effective_date"] = iso(praw["effective_date"].values)
    praw["termination_date"] = iso(praw["termination_date"].values)
    w = TableWriter(out, "providers", "CREDENTIALING"); w.add(praw.sample(frac=1, random_state=1)); written["providers"] = w.close()
    stats["providers_with_history_rows"] = int(prov["npi"].duplicated().sum())
    log(f"providers: {len(prov):,} rows")

    attrs, mraw = ent.build_members(rng, fake, n_members)
    w = TableWriter(out, "members", "FACETS"); w.add(mraw); written["members"] = w.close()
    stats["members_dob_non_iso"] = int((~mraw["dob"].str.match(r"^\d{4}-\d{2}-\d{2}$")).sum())
    log(f"members: {len(mraw):,}")

    el = ent.build_eligibility(rng, attrs, plans, lut)
    eraw, n_overlap = ent.eligibility_raw(rng, el)
    stats["eligibility_overlap_rows"] = n_overlap
    stats["eligibility_9999_sentinel"] = int((eraw["termination_date"] == "9999-12-31").sum())
    w = TableWriter(out, "eligibility", "FACETS"); w.add(eraw); written["eligibility"] = w.close()
    log(f"eligibility: {len(eraw):,} spans")

    mm = ent.member_months(el)
    a = attrs
    for c in ["state", "sex", "risk", "n_chronic", "is_diabetes", "is_hypertension", "is_asthma", "is_chf",
              "code_diabetes", "code_chf", "chronic_codes", "frequent_er", "oncology"]:
        mm[c] = a[c].values[mm["member_idx"].values]
    mm["age_m"] = a["age"].values[mm["member_idx"].values] - (29 - mm["month_idx"].values) / 12
    mm["ms"] = ent.month_start(mm["month_idx"].values)
    mm["dim"] = (ent.month_end(mm["month_idx"].values) - ent.month_start(mm["month_idx"].values)).astype(int) + 1
    g = mm.groupby("member_idx")["month_idx"]
    coverage = dict(zip(g.min().index, zip(g.min().values, g.max().values)))
    stats["member_months"] = len(mm)
    log(f"member months: {len(mm):,}")

    # ---- claims, auths, pharmacy by member chunk
    wh = TableWriter(out, "medical_claims_header", "CLAIMS_ADJ")
    wl = TableWriter(out, "medical_claims_line", "CLAIMS_ADJ")
    wh_r = TableWriter(out, "medical_claims_header", "CLAIMS_ADJ", tag="resend_", extract_ts=RESEND_TS)
    wl_r = TableWriter(out, "medical_claims_line", "CLAIMS_ADJ", tag="resend_", extract_ts=RESEND_TS)
    wa = TableWriter(out, "prior_authorizations", "UM_SYS")
    wp = TableWriter(out, "pharmacy_claims", "PBM", fmt="json")
    pharm = rx.build_pharmacies(rng, max(150, int(1500 * args.scale)), fake)

    for lo in range(0, n_members, args.chunk_members):
        hi = min(lo + args.chunk_members, n_members)
        mmc = mm[(mm["member_idx"] >= lo) & (mm["member_idx"] < hi)].reset_index(drop=True)
        b = med.Builder(rng, lut, oon)
        b.coverage = coverage
        med.build_events(rng, mmc, b)
        H, L, A, dups = med.finalize(rng, b, attrs, counters, stats)
        auths = med.build_auths(rng, A, H, attrs, counters, stats, lut)
        H, L = med.format_dates(H, L, rng)
        Lo = med.shape_lines(L)
        Ho = H[med.HEADER_COLS]
        wh.add(Ho.sample(frac=1, random_state=lo))
        wl.add(Lo)
        dmask = Ho["claim_id"].isin(dups)
        wh_r.add(Ho[dmask])
        wl_r.add(Lo[Lo["claim_id"].isin(dups)])
        stats["duplicate_line_rows"] += int(Lo["claim_id"].isin(dups).sum())
        wa.add(auths)
        wp.add(rx.build_pharmacy_chunk(rng, mmc, attrs, pharm, lut, counters, stats))
        log(f"members {lo:,}-{hi:,}: headers so far {wh.total + wh.nbuf:,}, lines {wl.total + wl.nbuf:,}, "
            f"rx {wp.total + wp.nbuf:,}")

    for k, wtr in [("medical_claims_header", wh), ("medical_claims_line", wl), ("prior_authorizations", wa),
                   ("pharmacy_claims", wp)]:
        written[k] = wtr.close()
    wh_r.close(); wl_r.close()
    written["medical_claims_header"].total += wh_r.total
    written["medical_claims_line"].total += wl_r.total

    # ---- manifest
    manifest = {
        "scale": args.scale, "seed": args.seed, "extract_ts": EXTRACT_TS,
        "coverage_window": ["2024-01-01", "2026-06-30"],
        "row_counts": {k: v.total for k, v in sorted(written.items())},
        "files": {k: v.files + (wh_r.files if k == "medical_claims_header" else wl_r.files if k == "medical_claims_line" else [])
                  for k, v in sorted(written.items())},
        "injected_issues": dict(sorted(stats.items())),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=int))
    log("done")
    print(json.dumps(manifest["row_counts"], indent=2))
    print(json.dumps(manifest["injected_issues"], indent=2, default=int))


if __name__ == "__main__":
    main()
