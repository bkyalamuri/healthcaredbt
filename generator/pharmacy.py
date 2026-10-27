"""Pharmacy (PBM) claims, emitted as nested JSON records."""
import numpy as np
import pandas as pd

from reference import DRUGS, ACUTE_DRUGS, PHARMACY_CHAINS
from medical import EXTRACT_DATE, ch


def build_pharmacies(rng, n, fake):
    chains, w = zip(*PHARMACY_CHAINS)
    chain = ch(rng, chains, n, w)
    state = ch(rng, ["CA", "NV", "AZ"], n, [0.6, 0.2, 0.2])
    npi = np.array([f"{1_500_000_000 + i * 31 + int(rng.integers(0, 31))}" for i in range(n)], dtype=object)
    name = np.array([f"{c} #{rng.integers(100, 9999)}" if c != "Independent" else f"{fake.last_name()} Family Pharmacy"
                     for c in chain], dtype=object)
    return pd.DataFrame({"npi": npi, "name": name, "chain": chain, "state": state})


def regimens(rng, a):
    """Per-member maintenance drug list driven by chronic conditions."""
    rows = []
    n = len(a)
    r = lambda: rng.random(n)
    rules = [
        ("is_diabetes", "metformin", 0.85), ("is_diabetes", "glipizide", 0.20), ("is_diabetes", "insulin_glargine", 0.25),
        ("is_diabetes", "semaglutide", 0.12), ("is_hypertension", "lisinopril", 0.45), ("is_hypertension", "losartan", 0.30),
        ("is_hypertension", "amlodipine", 0.40), ("is_hypertension", "hctz", 0.25), ("is_chf", "furosemide", 0.80),
        ("is_chf", "carvedilol", 0.70), ("is_chf", "sacubitril_valsartan", 0.25), ("is_chf", "apixaban", 0.20),
        ("is_asthma", "albuterol", 0.85), ("is_asthma", "fluticasone_salmeterol", 0.30), ("is_asthma", "montelukast", 0.35),
    ]
    for flag, drug, p in rules:
        m = a[flag].values & (r() < p)
        rows.append(pd.DataFrame({"member_idx": a["member_idx"].values[m], "drug": drug}))
    statin = (a["is_diabetes"].values | (a["is_hypertension"].values & (a["age"].values > 50))) & (r() < 0.55)
    rows.append(pd.DataFrame({"member_idx": a["member_idx"].values[statin],
                              "drug": np.where(rng.random(statin.sum()) < 0.7, "atorvastatin", "rosuvastatin")}))
    adult = a["age"].values >= 18
    for drug, p in [("levothyroxine", 0.06), ("sertraline", 0.045), ("escitalopram", 0.035), ("omeprazole", 0.07)]:
        m = adult & (r() < p)
        rows.append(pd.DataFrame({"member_idx": a["member_idx"].values[m], "drug": drug}))
    bio = a["biologic"].values
    rows.append(pd.DataFrame({"member_idx": a["member_idx"].values[bio],
                              "drug": np.where(rng.random(bio.sum()) < 0.6, "adalimumab", "etanercept")}))
    return pd.concat(rows, ignore_index=True)


def build_pharmacy_chunk(rng, mm, attrs, pharm, prov_lut, counters, stats):
    a = attrs.iloc[np.unique(mm["member_idx"].values)]
    reg = regimens(rng, a)
    reg["is90"] = attrs["mail_order_90"].values[reg["member_idx"].values] & (DRUGS_SPEC(reg["drug"]) == "N")
    reg["phase"] = rng.integers(0, 3, len(reg))
    x = reg.merge(mm[["member_idx", "month_idx", "lob", "state", "ms", "dim", "pcp_npi"]], on="member_idx")
    fill = np.where(x["is90"].values, ((x["month_idx"].values % 3) == x["phase"].values) & (rng.random(len(x)) < 0.85),
                    rng.random(len(x)) < 0.70)
    F = x[fill].copy()
    F["days_supply"] = np.where(F["is90"].values, 90, 30)

    # acute fills
    age = attrs["age"].values[mm["member_idx"].values]
    cnt = rng.poisson(0.05 * np.where(age < 18, 0.9, 1.0), len(mm))
    idx = np.repeat(np.arange(len(mm)), cnt)
    Ac = mm.iloc[idx][["member_idx", "month_idx", "lob", "state", "ms", "dim", "pcp_npi"]].copy()
    flu = np.isin((Ac["month_idx"].values % 12) + 1, [11, 12, 1, 2])
    Ac["drug"] = np.where(flu & (rng.random(len(Ac)) < 0.15), "oseltamivir", ch(rng, ACUTE_DRUGS, len(Ac)))
    Ac["days_supply"] = ch(rng, [5, 7, 10, 14], len(Ac))
    Ac["is90"] = False
    F = pd.concat([F, Ac], ignore_index=True)
    n = len(F)
    if not n:
        return []
    F["fill_date"] = F["ms"].values + rng.integers(0, F["dim"].values).astype("timedelta64[D]")

    # pricing
    d = F["drug"].values
    cost30 = np.array([DRUGS[k][5] for k in d], dtype=float)
    qty30 = np.array([DRUGS[k][6] for k in d], dtype=float)
    generic = np.array([DRUGS[k][2] for k in d])
    spec = np.array([DRUGS[k][3] for k in d])
    days = F["days_supply"].values.astype(int)
    ing = np.round(cost30 * days / 30 * rng.lognormal(0, 0.10, n), 2)
    fee = np.round(rng.uniform(1.5, 2.5, n), 2)
    lob = F["lob"].values
    copay = np.select(
        [lob == "Medicaid", (lob == "Commercial") & (spec == "Y"), (lob == "Commercial") & (generic == "Y"),
         lob == "Commercial", generic == "Y"],
        [np.where(rng.random(n) < 0.5, 0.0, 1.0), 150.0, 10.0, 40.0, 5.0], 45.0)
    copay = np.where(days == 90, copay * 2, copay)
    copay = np.minimum(copay, ing + fee)
    paid = np.round(ing + fee - copay, 2)
    rejected = rng.random(n) < 0.04
    status = np.where(rejected, "rejected", "paid").astype(object)
    ing = np.where(rejected, 0.0, ing)
    fee = np.where(rejected, 0.0, fee)
    paid = np.where(rejected, 0.0, paid)
    copay = np.where(rejected, 0.0, copay)
    qty = np.round(qty30 * days / 30, 1)

    # pharmacy + prescriber
    st = F["state"].values
    ph_idx = np.empty(n, dtype=int)
    for s in np.unique(st):
        pool = np.where(pharm["state"].values == s)[0]
        m = st == s
        ph_idx[m] = pool[rng.integers(0, len(pool), m.sum())]
    mail = F["is90"].values & (rng.random(n) < 0.7)
    mail_pool = np.where(pharm["chain"].values == "Pacific Mail Order Pharmacy")[0]
    if len(mail_pool):
        ph_idx[mail] = mail_pool[rng.integers(0, len(mail_pool), mail.sum())]
    prescriber = F["pcp_npi"].values.copy()

    F["adjudicated_ts"] = F["fill_date"].values.astype("datetime64[s]") + rng.integers(28800, 75600, n).astype("timedelta64[s]")
    keep = F["fill_date"].values <= EXTRACT_DATE

    start = counters["rx"]
    ids = np.array([f"RX{start + i:011d}" for i in range(n)], dtype=object)
    counters["rx"] += n
    member_id = attrs["member_id"].values[F["member_idx"].values]

    # NDC formatting mess: ~5% hyphenated 5-4-2
    ndc = np.array([DRUGS[k][0] for k in d], dtype=object)
    hy = rng.random(n) < 0.05
    ndc[hy] = [f"{x[:5]}-{x[5:9]}-{x[9:]}" for x in ndc[hy]]

    recs = []
    fd = pd.to_datetime(F["fill_date"]).dt.strftime("%Y-%m-%d").values
    ts = pd.to_datetime(F["adjudicated_ts"]).dt.strftime("%Y-%m-%dT%H:%M:%S").values
    for i in np.where(keep)[0]:
        p = pharm.iloc[ph_idx[i]]
        k = d[i]
        recs.append({
            "rx_claim_id": ids[i], "member_id": member_id[i], "fill_date": fd[i], "adjudicated_ts": ts[i],
            "pharmacy": {"npi": p["npi"], "name": p["name"], "chain": p["chain"]},
            "prescriber_npi": prescriber[i],
            "drug": {"ndc": ndc[i], "name": DRUGS[k][1], "generic_flag": DRUGS[k][2], "specialty_flag": DRUGS[k][3],
                     "therapeutic_class": DRUGS[k][4]},
            "quantity": float(qty[i]), "days_supply": int(days[i]),
            "ingredient_cost": float(ing[i]), "dispensing_fee": float(fee[i]),
            "plan_paid": float(paid[i]), "member_copay": float(copay[i]),
            "claim_status": status[i], "reversal_of_rx_claim_id": None,
        })
    # reversals (~3% of paid fills): negative amounts referencing the original
    paid_idx = [j for j, r in enumerate(recs) if r["claim_status"] == "paid"]
    rev = rng.choice(paid_idx, int(len(paid_idx) * 0.03), replace=False) if paid_idx else []
    for j in rev:
        o = recs[j]
        r = {**o, "pharmacy": dict(o["pharmacy"]), "drug": dict(o["drug"])}
        r["rx_claim_id"] = f"RX{counters['rx']:011d}"
        counters["rx"] += 1
        r["adjudicated_ts"] = (np.datetime64(o["adjudicated_ts"]) + np.timedelta64(int(rng.integers(1, 10)), "D")).astype(str)
        for c in ["ingredient_cost", "dispensing_fee", "plan_paid", "member_copay"]:
            r[c] = -o[c]
        r["quantity"] = -o["quantity"]
        r["claim_status"] = "reversed"
        r["reversal_of_rx_claim_id"] = o["rx_claim_id"]
        recs.append(r)
    stats["pharmacy_reversals"] += len(rev)
    stats["pharmacy_hyphenated_ndc"] += int(hy[keep].sum())
    return recs


def DRUGS_SPEC(s):
    return s.map(lambda k: DRUGS[k][3]).values
