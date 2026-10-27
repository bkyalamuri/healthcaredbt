"""Members, eligibility, plans and providers."""
import numpy as np
import pandas as pd

from reference import (STATES, LANGUAGES, RACE_ETH, build_plans, COVERAGE_TIERS_COMMERCIAL, SPECIALTIES,
                       ORG_NAME_PARTS, CHRONIC_DX)

WIN_START = np.datetime64("2024-01-01")
WIN_END = np.datetime64("2026-06-30")
N_MONTHS = 30  # Jan 2024 .. Jun 2026
AREA_CODES = {"CA": ["949", "714", "213", "310", "619", "916", "559", "951"], "NV": ["702", "775"], "AZ": ["602", "480", "520"]}


def month_start(idx):
    """Month index (0 = 2024-01) -> datetime64[D] first of month. Works for negative indexes."""
    idx = np.asarray(idx)
    return (np.datetime64("2024-01", "M") + idx).astype("datetime64[D]")


def month_end(idx):
    return (np.datetime64("2024-01", "M") + np.asarray(idx) + 1).astype("datetime64[D]") - 1


def weighted(rng, pairs, n):
    vals, w = zip(*pairs)
    w = np.array(w, dtype=float)
    return np.array(vals, dtype=object)[rng.choice(len(vals), n, p=w / w.sum())]


def fmt_dates(d, fmt):
    s = pd.Series(pd.to_datetime(d))
    return s.dt.strftime(fmt).where(s.notna(), None).values


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------
def build_plans_df(rng):
    rows = []
    for plan_id, name, lob, tier, st, ded, oop in build_plans():
        for yr in (2024, 2025, 2026):
            infl = 1 + 0.04 * (yr - 2024)
            rows.append({"plan_id": plan_id, "plan_name": name, "lob": lob, "metal_tier": tier, "state": st,
                         "deductible": int(round(ded * infl, -1)), "oop_max": int(round(oop * infl, -1)),
                         "effective_year": yr})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
def build_providers(rng, fake, n):
    groups = list(SPECIALTIES)
    shares = np.array([SPECIALTIES[g][1] for g in groups])
    grp = np.array(groups, dtype=object)[rng.choice(len(groups), n, p=shares / shares.sum())]
    st_names = list(STATES)
    st_w = np.array([STATES[s]["weight"] for s in st_names])
    state = np.array(st_names, dtype=object)[rng.choice(3, n, p=st_w)]
    npi_num = 1_100_000_000 + np.arange(n) * 29 + rng.integers(0, 29, n)
    npi = np.array([str(x) for x in npi_num], dtype=object)

    spec_code, spec_desc, ptype, name = [], [], [], []
    county, city, zipc = [], [], []
    for g, st in zip(grp, state):
        opts, _, is_org = SPECIALTIES[g]
        code, desc = opts[rng.integers(len(opts))]
        spec_code.append(code)
        spec_desc.append(desc)
        cty = STATES[st]["counties"][rng.integers(len(STATES[st]["counties"]))]
        county.append(cty[0])
        c = cty[1][rng.integers(len(cty[1]))]
        city.append(c)
        zipc.append(cty[2] + f"{rng.integers(1, 99):02d}")
        if is_org:
            ptype.append("organization")
            a, b = ORG_NAME_PARTS.get(g, ORG_NAME_PARTS["group"])
            name.append(f"{a[rng.integers(len(a))]} {b[rng.integers(len(b))]} - {c}")
        else:
            ptype.append("individual")
            cred = {"363L00000X": "NP", "225100000X": "PT", "103T00000X": "PhD", "1041C0700X": "LCSW"}.get(code,
                    "DO" if rng.random() < 0.12 else "MD")
            name.append(f"{fake.last_name().upper()}, {fake.first_name().upper()} {cred}")

    tax_pool = [f"{rng.integers(10, 99)}-{rng.integers(1000000, 9999999)}" for _ in range(max(50, n // 6))]
    df = pd.DataFrame({
        "npi": npi, "tax_id": np.array(tax_pool, dtype=object)[rng.integers(0, len(tax_pool), n)],
        "provider_name": name, "provider_type": ptype, "specialty_code": spec_code, "specialty_desc": spec_desc,
        "address_line_1": [fake.street_address() for _ in range(n)], "city": city, "county": county,
        "state": state, "zip": zipc,
        "network_status": np.where(rng.random(n) < 0.90, "in", "out"),
        "effective_date": month_start(-rng.integers(1, 168, n)),
        "termination_date": np.full(n, np.datetime64("NaT"), dtype="datetime64[D]"),
        "_group": grp,
    })
    # ~3% of providers leave the network during the window
    term = rng.random(n) < 0.03
    df.loc[term, "termination_date"] = month_end(rng.integers(6, 28, term.sum()))

    # ~15% of NPIs have a second history row (address move or network status change)
    chg = np.where((rng.random(n) < 0.15) & ~term)[0]
    change_month = rng.integers(3, 27, len(chg))
    new_rows = df.iloc[chg].copy()
    df.loc[df.index[chg], "termination_date"] = month_start(change_month) - 1
    new_rows["effective_date"] = month_start(change_month)
    flip = rng.random(len(chg)) < 0.4
    new_rows.loc[flip, "network_status"] = np.where(new_rows.loc[flip, "network_status"] == "in", "out", "in")
    new_rows.loc[~flip, "address_line_1"] = [fake.street_address() for _ in range((~flip).sum())]
    df = pd.concat([df, new_rows], ignore_index=True).sort_values(["npi", "effective_date"]).reset_index(drop=True)
    return df


def provider_lookup(prov):
    """(state, group) -> array of NPIs, plus network status per NPI (first row)."""
    first = prov.drop_duplicates("npi")
    lut = {}
    for (st, g), sub in first.groupby(["state", "_group"]):
        lut[(st, g)] = sub["npi"].values
    for g, sub in first.groupby("_group"):
        lut[("ANY", g)] = sub["npi"].values
    oon = dict(zip(first["npi"], first["network_status"] == "out"))
    return lut, oon


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------
def build_members(rng, fake, n):
    lob = weighted(rng, [("Medicaid", 0.55), ("Commercial", 0.35), ("Medicare Advantage", 0.10)], n)
    rel = np.full(n, "18", dtype=object)  # 18 = self
    r = rng.random(n)
    com, mcd = lob == "Commercial", lob == "Medicaid"
    rel[com & (r < 0.15)] = "01"
    rel[com & (r >= 0.15) & (r < 0.45)] = "19"
    rel[mcd & (r < 0.05)] = "01"
    rel[mcd & (r >= 0.05) & (r < 0.40)] = "19"

    st_names = list(STATES)
    st_w = np.array([STATES[s]["weight"] for s in st_names])
    state = np.array(st_names, dtype=object)[rng.choice(3, n, p=st_w)]

    # ages
    age = np.empty(n)
    ma = lob == "Medicare Advantage"
    age[ma] = 65 + rng.gamma(2.0, 5.0, ma.sum())
    child = rel == "19"
    age[child] = np.where(com[child], rng.uniform(0, 26, child.sum()), rng.uniform(0, 19, child.sum()))
    adult = ~ma & ~child
    age[adult] = np.where(mcd[adult], 19 + rng.gamma(2.2, 9.0, adult.sum()), rng.uniform(22, 64.9, adult.sum()))
    age = np.clip(age, 0, 99)
    ref = np.datetime64("2026-06-30")
    dob = ref - (age * 365.25).astype(int).astype("timedelta64[D]")

    sex = np.where(rng.random(n) < 0.51, "F", "M").astype(object)
    sex[rng.random(n) < 0.003] = "U"

    member_num = 12_000_000 + np.arange(n) * 41 + rng.integers(0, 41, n)
    member_id = np.array([f"PCH{x:09d}" for x in member_num], dtype=object)

    # link dependents to a subscriber in the same LOB + state
    subscriber = member_id.copy()
    for lb in ["Commercial", "Medicaid"]:
        for st in st_names:
            subs = np.where((lob == lb) & (state == st) & (rel == "18"))[0]
            deps = np.where((lob == lb) & (state == st) & (rel != "18"))[0]
            if len(subs) and len(deps):
                subscriber[deps] = member_id[subs[rng.integers(0, len(subs), len(deps))]]
    idx_of = {m: i for i, m in enumerate(member_id)}
    sub_idx = np.array([idx_of[s] for s in subscriber])

    first = [fake.first_name_female() if s == "F" else fake.first_name_male() for s in sex]
    last = np.array([fake.last_name() for _ in range(n)], dtype=object)
    last = last[sub_idx]  # dependents share the subscriber's last name ...
    keep_own = (rel != "18") & (rng.random(n) < 0.12)  # ... mostly
    last[keep_own] = [fake.last_name() for _ in range(keep_own.sum())]

    county, city, zipc = np.empty(n, dtype=object), np.empty(n, dtype=object), np.empty(n, dtype=object)
    for i, st in enumerate(state):
        cty = STATES[st]["counties"][rng.integers(len(STATES[st]["counties"]))]
        county[i], city[i], zipc[i] = cty[0], cty[1][rng.integers(len(cty[1]))], cty[2] + f"{rng.integers(1, 99):02d}"
    addr = np.array([fake.street_address() for _ in range(n)], dtype=object)
    for arr in (county, city, zipc, addr):
        arr[:] = arr[sub_idx]

    # chronic conditions by age
    def prev(p_young, p_mid, p_old, p_senior):
        p = np.select([age < 30, age < 50, age < 65], [p_young, p_mid, p_old], p_senior)
        return rng.random(n) < p
    diabetes = prev(0.015, 0.08, 0.16, 0.26)
    hypertension = prev(0.04, 0.20, 0.42, 0.62)
    asthma = rng.random(n) < np.where(age < 18, 0.10, 0.075)
    chf = prev(0.001, 0.005, 0.025, 0.09)
    flags = {"diabetes": diabetes, "hypertension": hypertension, "asthma": asthma, "chf": chf}
    codes = {}
    for cond, (opts, w) in CHRONIC_DX.items():
        c = np.array(opts, dtype=object)[rng.choice(len(opts), n, p=w)]
        codes[cond] = np.where(flags[cond], c, None)
    chronic_str = np.array(["|".join(x for x in row if x) for row in zip(*codes.values())], dtype=object)

    risk = rng.lognormal(-0.5, 1.0, n)
    attrs = pd.DataFrame({
        "member_idx": np.arange(n), "member_id": member_id, "dob": dob, "age": age, "sex": sex, "state": state,
        "lob0": lob, "rel": rel, "risk": risk, "n_chronic": diabetes.astype(int) + hypertension + asthma + chf,
        **{f"is_{k}": v for k, v in flags.items()}, **{f"code_{k}": v for k, v in codes.items()},
        "chronic_codes": chronic_str,
        "frequent_er": rng.random(n) < 0.01,
        "oncology": (rng.random(n) < 0.003) & (sex == "F") & (age > 35),
        "biologic": rng.random(n) < 0.003,
        "mail_order_90": rng.random(n) < 0.25,
    })

    # ---- raw members file (with source-system inconsistencies)
    src = np.where(mcd & (rng.random(n) < 0.40), "LEGACY_MMIS", "FACETS").astype(object)
    portal = (src == "FACETS") & (rng.random(n) < 0.04)
    src[portal] = "ENROLL_PORTAL"
    dob_iso = fmt_dates(dob, "%Y-%m-%d")
    dob_out = dob_iso.copy()
    legacy = src == "LEGACY_MMIS"
    dob_out[legacy] = fmt_dates(dob[legacy], "%Y%m%d")
    manual = (src == "FACETS") & (rng.random(n) < 0.06)
    dob_out[manual] = fmt_dates(dob[manual], "%m/%d/%Y")
    gender = sex.copy()
    gender[legacy] = np.select([sex[legacy] == "M", sex[legacy] == "F"], ["1", "2"], "9")
    gender[portal] = np.select([sex[portal] == "M", sex[portal] == "F"], ["Male", "Female"], "Unknown")

    ac = np.array([AREA_CODES[s][rng.integers(len(AREA_CODES[s]))] for s in state], dtype=object)
    line = rng.integers(100, 200, n)
    style = rng.integers(0, 3, n)
    phone = np.array([f"({a}) 555-{l:04d}" if s == 0 else (f"{a}-555-{l:04d}" if s == 1 else f"{a}555{l:04d}")
                      for a, l, s in zip(ac, line, style)], dtype=object)
    pr = rng.random(n)
    phone[pr < 0.08] = None
    phone[(pr >= 0.08) & (pr < 0.09)] = "N/A"
    phone[(pr >= 0.09) & (pr < 0.10)] = ""
    email = np.array([f"{f.lower()}.{l.lower().replace(' ', '')}{rng.integers(1, 999)}@example.com"
                      for f, l in zip(first, last)], dtype=object)
    er = rng.random(n)
    email[er < 0.30] = None
    email[(er >= 0.30) & (er < 0.31)] = "NULL"

    created = WIN_START - rng.integers(0, 3000, n).astype("timedelta64[D]")
    updated = WIN_START + rng.integers(0, 900, n).astype("timedelta64[D]")
    ssn = np.array([f"9{rng.integers(0, 99):02d}-{rng.integers(1, 99):02d}-{rng.integers(1, 9999):04d}"
                    for _ in range(n)], dtype=object)

    raw = pd.DataFrame({
        "member_id": member_id, "subscriber_id": subscriber, "relationship_code": rel,
        "first_name": first, "last_name": last, "dob": dob_out, "gender": gender, "ssn": ssn,
        "address_line_1": addr, "city": city, "county": county, "state": state, "zip": zipc,
        "phone": phone, "email": email,
        "preferred_language": weighted(rng, LANGUAGES, n), "race_ethnicity_code": weighted(rng, RACE_ETH, n),
        "created_at": fmt_dates(created, "%Y-%m-%d %H:%M:%S"),
        "updated_at": fmt_dates(updated, "%Y-%m-%d %H:%M:%S"),
        "_source_system": src,
    })
    return attrs, raw


# ---------------------------------------------------------------------------
# Eligibility spans
# ---------------------------------------------------------------------------
def build_eligibility(rng, attrs, plans, prov_lut):
    n = len(attrs)
    plan_ids = plans.drop_duplicates("plan_id")
    by_lob_state = {k: g["plan_id"].values for k, g in plan_ids.groupby(["lob", "state"])}
    com_tier_w = {"BRO": 0.25, "SIL": 0.40, "GOL": 0.25, "PLA": 0.10}
    nspans_p = {"Medicaid": [0.65, 0.27, 0.08], "Commercial": [0.82, 0.15, 0.03], "Medicare Advantage": [0.92, 0.07, 0.01]}

    def choose_plan(lob, st):
        opts = by_lob_state[(lob, st)]
        if lob == "Commercial":
            w = np.array([com_tier_w[p.split("-")[-1]] for p in opts])
            return opts[rng.choice(len(opts), p=w / w.sum())]
        if lob == "Medicare Advantage":
            return opts[rng.choice(len(opts), p=[0.65, 0.35])]
        return opts[0]

    rows = []
    lobs, states, rels = attrs["lob0"].values, attrs["state"].values, attrs["rel"].values
    age = attrs["age"].values
    for i in range(n):
        lob, st = lobs[i], states[i]
        pre = rng.random() < 0.72
        cur = 0 if pre else int(rng.integers(1, 28))
        k = rng.choice(3, p=nspans_p[lob]) + 1
        for s in range(k):
            last = s == k - 1
            length = int(rng.geometric(1 / 11)) + 1
            end = cur + length - 1
            open_ended = (last and rng.random() < 0.78) or end >= N_MONTHS - 1
            eff_idx = cur
            if s == 0 and pre:
                eff_idx = -int(rng.integers(1, 96))
            tier = "IND"
            if lob == "Commercial":
                tier = "EE" if rels[i] == "18" and rng.random() < 0.45 else weighted(rng, COVERAGE_TIERS_COMMERCIAL, 1)[0]
            rows.append((i, choose_plan(lob, st), lob, eff_idx, None if open_ended else end, tier))
            if open_ended:
                break
            cur = end + 1 + int(rng.integers(1, 5))
            if cur > N_MONTHS - 2:
                break
            # plan / LOB change on re-enrollment
            if lob == "Medicaid" and age[i] >= 19 and rng.random() < 0.10:
                lob = "Commercial"
            if lob == "Commercial" and age[i] >= 64.5:
                lob = "Medicare Advantage"

    el = pd.DataFrame(rows, columns=["member_idx", "plan_id", "lob", "eff_idx", "end_idx", "coverage_tier"])
    el["effective_date"] = month_start(el["eff_idx"].values)
    el["termination_date"] = np.where(el["end_idx"].isna(), np.datetime64("NaT"),
                                      month_end(el["end_idx"].fillna(0).astype(int).values))
    el["termination_date"] = pd.to_datetime(el["termination_date"])
    el["member_id"] = attrs["member_id"].values[el["member_idx"].values]
    st = attrs["state"].values[el["member_idx"].values]
    pcp = np.empty(len(el), dtype=object)
    for s in np.unique(st):
        m = st == s
        pool = prov_lut[(s, "pcp")]
        pcp[m] = pool[rng.integers(0, len(pool), m.sum())]
    el["pcp_npi"] = pcp
    return el


def eligibility_raw(rng, el):
    """Clean spans -> raw extract with overlaps and sentinel termination dates."""
    raw = el[["member_id", "plan_id", "lob", "effective_date", "termination_date", "pcp_npi", "coverage_tier"]].copy()
    # overlapping retro rows (~0.5% of members)
    mem = raw["member_id"].unique()
    pick = set(rng.choice(mem, int(len(mem) * 0.005), replace=False))
    ov = raw[raw["member_id"].isin(pick)].groupby("member_id").tail(1).copy()
    eff = ov["effective_date"].values.astype("datetime64[M]") + 1
    ov["effective_date"] = eff.astype("datetime64[D]")
    term = ov["termination_date"].values.astype("datetime64[M]")
    ov["termination_date"] = np.where(pd.isna(ov["termination_date"]).values, np.datetime64("NaT"),
                                      (term + 2).astype("datetime64[D]") - 1)
    raw = pd.concat([raw, ov], ignore_index=True)
    raw["effective_date"] = fmt_dates(raw["effective_date"].values, "%Y-%m-%d")
    term = fmt_dates(raw["termination_date"].values, "%Y-%m-%d")
    open_ = pd.isna(term)
    sentinel = open_ & (rng.random(len(raw)) < 0.30)
    term = np.where(sentinel, "9999-12-31", term)
    raw["termination_date"] = term
    raw = raw.sample(frac=1, random_state=int(rng.integers(1e9))).reset_index(drop=True)
    return raw, len(ov)


def member_months(el):
    """Clean spans -> one row per member per covered month inside the window."""
    s = el["eff_idx"].clip(lower=0).values
    e = el["end_idx"].fillna(N_MONTHS - 1).clip(upper=N_MONTHS - 1).astype(int).values
    ln = np.maximum(e - s + 1, 0)
    rep = np.repeat(np.arange(len(el)), ln)
    offs = np.arange(ln.sum()) - np.repeat(np.cumsum(ln) - ln, ln)
    mm = pd.DataFrame({
        "member_idx": el["member_idx"].values[rep], "month_idx": s[rep] + offs,
        "lob": el["lob"].values[rep], "plan_id": el["plan_id"].values[rep], "pcp_npi": el["pcp_npi"].values[rep],
    })
    return mm
