"""Medical claims (header + line) and prior authorizations."""
import numpy as np
import pandas as pd

from reference import PROC, REV, DRG, DRG_BASE_RATE, DENIAL_WEIGHTS, ACUTE_OFFICE_DX, ER_DX, RESPIRATORY_ER_DX
from entities import month_start, WIN_END

EXTRACT_DATE = np.datetime64("2026-07-31")
LOB_FACTOR = {"Commercial": 2.6, "Medicare Advantage": 1.8, "Medicaid": 1.3}
NAT = np.datetime64("NaT", "D")


def ch(rng, vals, n, p=None):
    vals = np.asarray(vals, dtype=object)
    if p is not None:
        p = np.asarray(p, dtype=float)
        p = p / p.sum()
    return vals[rng.choice(len(vals), n, p=p)]


class Builder:
    def __init__(self, rng, lut, oon):
        self.rng, self.lut, self.oon = rng, lut, oon
        self.H, self.L, self.auth = [], [], []
        self.ck = 0

    # -- helpers ------------------------------------------------------------
    def new_ck(self, n):
        out = np.arange(self.ck, self.ck + n)
        self.ck += n
        return out

    def npi(self, states, group):
        out = np.empty(len(states), dtype=object)
        for st in np.unique(states):
            m = states == st
            pool = self.lut.get((st, group), self.lut[("ANY", group)])
            out[m] = pool[self.rng.integers(0, len(pool), m.sum())]
        return out

    def header(self, E, ck, kind, claim_type, bill_type, pos, billing, rendering, d_from, d_to,
               primary_dx, sec_dx=None, drg=None, admit=None, discharge=None):
        n = len(ck)
        nat = np.full(n, NAT)
        self.H.append(pd.DataFrame({
            "ck": ck, "member_idx": E["member_idx"].values, "lob": E["lob"].values, "plan_id": E["plan_id"].values,
            "kind": kind, "claim_type": claim_type, "bill_type": bill_type, "place_of_service": pos,
            "billing_npi": billing, "rendering_npi": rendering,
            "service_from_date": d_from, "service_to_date": d_to,
            "admit_date": admit if admit is not None else nat, "discharge_date": discharge if discharge is not None else nat,
            "primary_dx_code": primary_dx,
            "sec_dx": sec_dx if sec_dx is not None else E["chronic_codes"].values,
            "drg_code": drg,
        }))

    def lines(self, ck, proc, rev, units, line_date, base=None, mod=None):
        n = len(ck)
        proc = np.asarray(proc, dtype=object) if proc is not None else np.full(n, None, dtype=object)
        rev = np.asarray(rev, dtype=object) if rev is not None else np.full(n, None, dtype=object)
        if base is None:
            base = np.array([REV[r][1] if r is not None else PROC[p][2] for p, r in zip(proc, rev)], dtype=float)
        self.L.append(pd.DataFrame({
            "ck": ck, "procedure_code": proc, "revenue_code": rev,
            "modifier_1": mod if mod is not None else np.full(n, None, dtype=object),
            "units": np.asarray(units), "base_unit": base, "line_service_date": line_date,
        }))

    def need_auth(self, E, ck, npi, service_type, proc, dates, urgency):
        self.auth.append(pd.DataFrame({"ck": ck, "member_idx": E["member_idx"].values, "requesting_npi": npi,
                                       "service_type": service_type, "procedure_code": proc,
                                       "service_date": dates, "urgency": urgency}))


def events(rng, mm, rate):
    counts = rng.poisson(np.clip(rate, 0, None))
    idx = np.repeat(np.arange(len(mm)), counts)
    E = mm.iloc[idx].reset_index(drop=True)
    E["svc"] = E["ms"].values + rng.integers(0, E["dim"].values).astype("timedelta64[D]")
    return E


def pick_chronic(rng, codes):
    out = np.empty(len(codes), dtype=object)
    for i, c in enumerate(codes):
        parts = c.split("|")
        out[i] = parts[rng.integers(len(parts))]
    return out


def drop_code(sec, prim):
    return np.array(["|".join(x for x in s.split("|") if x and x != p) for s, p in zip(sec, prim)], dtype=object)


def acute_or_chronic(rng, E, p_chronic=0.55, pool=ACUTE_OFFICE_DX):
    n = len(E)
    prim = ch(rng, pool, n)
    has = (E["n_chronic"].values > 0) & (rng.random(n) < p_chronic)
    if has.any():
        prim[has] = pick_chronic(rng, E["chronic_codes"].values[has])
    return prim, drop_code(E["chronic_codes"].values, prim)


# ---------------------------------------------------------------------------
def build_events(rng, mm, b):
    n = len(mm)
    age = mm["age_m"].values
    agef = np.select([age < 18, age < 65], [0.8, 1.0], 1.6)
    lobu = mm["lob"].map({"Medicaid": 1.1, "Commercial": 0.9, "Medicare Advantage": 1.3}).values
    r = mm["risk"].values
    nc = mm["n_chronic"].values
    month = (mm["month_idx"].values % 12) + 1
    flu = np.isin(month, [11, 12, 1, 2])
    st = mm["state"].values

    # 1. office visits -----------------------------------------------------
    E = events(rng, mm, 0.13 * agef * lobu * np.sqrt(r) * (1 + 0.35 * nc))
    m = len(E)
    if m:
        ck = b.new_ck(m)
        prim, sec = acute_or_chronic(rng, E)
        pos = ch(rng, ["11", "02", "10", "20"], m, [0.85, 0.05, 0.05, 0.05])
        rend = E["pcp_npi"].values.copy()
        other = rng.random(m) < 0.30
        rend[other] = b.npi(E["state"].values[other], "pcp")
        spec = (rng.random(m) < 0.25) & (E["n_chronic"].values > 0)
        for flag, grp in [("is_chf", "cardiology"), ("is_diabetes", "endo"), ("is_asthma", "pulm"), ("is_hypertension", "cardiology")]:
            mk = spec & E[flag].values
            rend[mk] = b.npi(E["state"].values[mk], grp)
            spec &= ~mk
        bill = np.where(rng.random(m) < 0.55, rend, b.npi(E["state"].values, "group"))
        b.header(E, ck, "office", "professional", None, pos, bill, rend, E["svc"].values, E["svc"].values, prim, sec)
        new = rng.random(m) < 0.10
        em = np.where(new, ch(rng, ["99202", "99203", "99204", "99205"], m, [.1, .4, .38, .12]),
                      ch(rng, ["99212", "99213", "99214", "99215"], m, [.1, .4, .38, .12]))
        b.lines(ck, em, None, np.ones(m), E["svc"].values)
        lab = rng.random(m) < 0.30
        b.lines(ck[lab], np.full(lab.sum(), "36415"), None, np.ones(lab.sum()), E["svc"].values[lab])
        b.lines(ck[lab], ch(rng, ["80053", "85025", "80061", "84443", "81001", "87880"], lab.sum()), None,
                np.ones(lab.sum()), E["svc"].values[lab])
        vac = (rng.random(m) < 0.12) & np.isin(((E["month_idx"].values % 12) + 1), [10, 11, 12, 1])
        b.lines(ck[vac], np.full(vac.sum(), "90686"), None, np.ones(vac.sum()), E["svc"].values[vac])
        b.lines(ck[vac], np.full(vac.sum(), "90471"), None, np.ones(vac.sum()), E["svc"].values[vac])
        ecg = (rng.random(m) < 0.08) & (E["age_m"].values >= 50)
        b.lines(ck[ecg], np.full(ecg.sum(), "93000"), None, np.ones(ecg.sum()), E["svc"].values[ecg])
        inj = rng.random(m) < 0.04
        b.lines(ck[inj], ch(rng, ["J1885", "J1100"], inj.sum()), None, rng.integers(1, 10, inj.sum()), E["svc"].values[inj])

    # 2. lab claims (incl. HbA1c for diabetics) -----------------------------
    dia = mm["is_diabetes"].values
    for rate, a1c in [(0.05 * agef * (1 + 0.5 * nc), False), (0.09 * dia, True)]:
        E = events(rng, mm, rate)
        m = len(E)
        if not m:
            continue
        ck = b.new_ck(m)
        if a1c:
            prim = E["code_diabetes"].values.astype(object)
            sec = drop_code(E["chronic_codes"].values, prim)
        else:
            prim, sec = acute_or_chronic(rng, E, 0.5, ["Z00.00", "R53.83", "E78.5", "E03.9", "N39.0"])
        bill = b.npi(E["state"].values, "lab")
        b.header(E, ck, "lab", "professional", None, np.full(m, "81"), bill, np.full(m, None, dtype=object),
                 E["svc"].values, E["svc"].values, prim, sec)
        b.lines(ck, np.full(m, "36415"), None, np.ones(m), E["svc"].values)
        if a1c:
            b.lines(ck, ch(rng, ["83036", "83037"], m, [0.9, 0.1]), None, np.ones(m), E["svc"].values)
            extra = rng.random(m) < 0.5
            b.lines(ck[extra], np.full(extra.sum(), "80053"), None, np.ones(extra.sum()), E["svc"].values[extra])
        else:
            k = rng.integers(1, 4, m)
            rep = np.repeat(np.arange(m), k)
            b.lines(ck[rep], ch(rng, ["80053", "85025", "80061", "84443", "81001"], len(rep)), None,
                    np.ones(len(rep)), E["svc"].values[rep])

    # 3. ER visits -------------------------------------------------------------
    lob_er = mm["lob"].map({"Medicaid": 1.7, "Commercial": 0.65, "Medicare Advantage": 1.25}).values
    er_rate = (0.011 * lob_er * np.where(flu, 1.4, 0.9) * (1 + mm["is_asthma"].values + 0.8 * mm["is_chf"].values)
               * r ** 0.4 * np.where(mm["frequent_er"].values, 8, 1))
    E = events(rng, mm, er_rate)
    m = len(E)
    if m:
        eflu = np.isin((E["month_idx"].values % 12) + 1, [11, 12, 1, 2])
        prim = np.where(rng.random(m) < np.where(eflu, 0.6, 0.25), ch(rng, RESPIRATORY_ER_DX, m), ch(rng, ER_DX, m))
        ast = E["is_asthma"].values & (rng.random(m) < 0.30)
        prim[ast] = "J45.901"
        sec = drop_code(E["chronic_codes"].values, prim)
        hosp = b.npi(E["state"].values, "hospital")
        # facility claim
        ck = b.new_ck(m)
        b.header(E, ck, "er_facility", "institutional", np.full(m, "0131"), np.full(m, None, dtype=object), hosp,
                 np.full(m, None, dtype=object), E["svc"].values, E["svc"].values, prim, sec)
        rv = ch(rng, ["0450", "0451", "0452", "0456", "0459"], m, [0.80, 0.04, 0.08, 0.05, 0.03])
        lvl = ch(rng, ["99283", "99284", "99285"], m, [0.35, 0.45, 0.20])
        b.lines(ck, lvl, rv, np.ones(m), E["svc"].values)
        for code, p, cpt in [("0300", 0.6, "80053"), ("0320", 0.4, "71046"), ("0250", 0.5, None), ("0350", 0.12, "70450")]:
            mk = rng.random(m) < p
            b.lines(ck[mk], np.full(mk.sum(), cpt, dtype=object), np.full(mk.sum(), code), np.ones(mk.sum()),
                    E["svc"].values[mk])
        # professional claim
        ck2 = b.new_ck(m)
        doc = b.npi(E["state"].values, "er_doc")
        b.header(E, ck2, "er_professional", "professional", None, np.full(m, "23"), b.npi(E["state"].values, "group"),
                 doc, E["svc"].values, E["svc"].values, prim, sec)
        b.lines(ck2, ch(rng, ["99282", "99283", "99284", "99285"], m, [.1, .35, .4, .15]), None, np.ones(m), E["svc"].values)
        mk = rng.random(m) < 0.2
        b.lines(ck2[mk], np.full(mk.sum(), "93000"), None, np.ones(mk.sum()), E["svc"].values[mk])
        # ambulance
        amb = np.where(rng.random(m) < 0.10)[0]
        if len(amb):
            Ea = E.iloc[amb].reset_index(drop=True)
            ck3 = b.new_ck(len(amb))
            b.header(Ea, ck3, "ambulance", "professional", None, np.full(len(amb), "41"), b.npi(Ea["state"].values, "ambulance"),
                     np.full(len(amb), None, dtype=object), Ea["svc"].values, Ea["svc"].values, prim[amb], sec[amb])
            b.lines(ck3, np.full(len(amb), "A0427"), None, np.ones(len(amb)), Ea["svc"].values)
            b.lines(ck3, np.full(len(amb), "A0425"), None, rng.integers(3, 25, len(amb)), Ea["svc"].values)

    # 4. imaging (incl. screening mammograms) ---------------------------------
    women = (mm["sex"].values == "F") & (age >= 40) & (age < 75)
    for rate, mammo in [(0.018 * agef * np.sqrt(r), False), (0.012 * women, True)]:
        E = events(rng, mm, rate)
        m = len(E)
        if not m:
            continue
        if mammo:
            code = np.full(m, "77067", dtype=object)
        else:
            code = ch(rng, ["71046", "72148", "73721", "74177", "70450", "93306", "71045"], m, [.28, .14, .12, .12, .10, .09, .15])
        dxmap = {"77067": "Z12.31", "72148": "M54.50", "73721": "M25.561", "74177": "R10.9", "70450": "R51.9",
                 "71046": "R05.9", "71045": "J18.9", "93306": "R07.9"}
        prim = np.array([dxmap[c] for c in code], dtype=object)
        chf = (code == "93306") & E["is_chf"].values
        prim[chf] = E["code_chf"].values[chf]
        sec = drop_code(E["chronic_codes"].values, prim)
        ck = b.new_ck(m)
        rad = b.npi(E["state"].values, "radiology")
        center = rng.random(m) < 0.55
        bill = np.where(center, b.npi(E["state"].values, "imaging_center"), b.npi(E["state"].values, "group"))
        b.header(E, ck, "imaging", "professional", None, np.where(center, "11", "22"), bill, rad,
                 E["svc"].values, E["svc"].values, prim, sec)
        b.lines(ck, code, None, np.ones(m), E["svc"].values)
        adv = np.isin(code, ["72148", "73721", "74177", "70450"])
        if adv.any():
            Ea = E[adv]
            b.need_auth(Ea, ck[adv], E["pcp_npi"].values[adv], np.full(adv.sum(), "Advanced Imaging"), code[adv],
                        E["svc"].values[adv], np.full(adv.sum(), "standard"))

    # 5. inpatient admissions + 30-day readmissions -----------------------------
    ipf = np.select([age < 18, age < 65], [0.4, 1.0], 3.2)
    ip_rate = 0.0045 * ipf * (1 + 4 * mm["is_chf"].values + 0.8 * dia) * r ** 0.6
    mat_rate = 0.0045 * ((mm["sex"].values == "F") & (age >= 18) & (age < 45))
    E1 = events(rng, mm, ip_rate)
    E1["maternity"] = False
    E2 = events(rng, mm, mat_rate)
    E2["maternity"] = True
    E = pd.concat([E1, E2], ignore_index=True)
    if len(E):
        m = len(E)
        med_drgs = ["194", "871", "470", "392", "690", "313", "885", "638", "202", "291"]
        drg = ch(rng, med_drgs, m, [.18, .12, .10, .14, .12, .14, .05, .05, .05, .05])
        drg[(drg == "470") & (E["age_m"].values < 50)] = "392"
        for flag, code, p in [("is_chf", "291", 0.55), ("is_diabetes", "638", 0.20), ("is_asthma", "202", 0.25)]:
            mk = E[flag].values & (rng.random(m) < p)
            drg[mk] = code
        mat = E["maternity"].values
        drg[mat] = ch(rng, ["807", "788"], mat.sum(), [0.68, 0.32])
        # readmissions (one generation)
        los = np.maximum(1, np.round(rng.gamma(2.0, np.array([DRG[d][2] for d in drg]) / 2))).astype(int)
        disch = E["svc"].values + los.astype("timedelta64[D]")
        readm = (~mat) & (rng.random(m) < np.where(E["is_chf"].values, 0.25, 0.10))
        R = E[readm].copy()
        R["svc"] = disch[readm] + rng.integers(2, 30, readm.sum()).astype("timedelta64[D]")
        rdrg = np.where(rng.random(len(R)) < 0.6, drg[readm], ch(rng, ["194", "871", "392", "690", "313"], len(R)))
        rlos = np.maximum(1, np.round(rng.gamma(2.0, np.array([DRG[d][2] for d in rdrg]) / 2))).astype(int)
        E = pd.concat([E, R], ignore_index=True)
        drg = np.concatenate([drg, rdrg])
        los = np.concatenate([los, rlos])
        keep = E["svc"].values <= WIN_END
        E, drg, los = E[keep].reset_index(drop=True), drg[keep], los[keep]
        m = len(E)
        admit = E["svc"].values
        disch = admit + los.astype("timedelta64[D]")
        prim = np.array([DRG[d][4] for d in drg], dtype=object)
        chf_m = (drg == "291") & E["is_chf"].values
        prim[chf_m] = np.where(rng.random(chf_m.sum()) < 0.5, "I50.23", E["code_chf"].values[chf_m])
        sec = drop_code(E["chronic_codes"].values, prim)
        hosp = b.npi(E["state"].values, "hospital")
        ck = b.new_ck(m)
        b.header(E, ck, "inpatient", "institutional", np.full(m, "0111"), np.full(m, None, dtype=object), hosp,
                 np.full(m, None, dtype=object), admit, disch, prim, sec, drg=drg, admit=admit, discharge=disch)
        surg = np.array([DRG[d][3] for d in drg], dtype=bool)
        b.lines(ck, None, np.full(m, "0120"), los, admit)
        for code, mk in [("0250", np.ones(m, bool)), ("0300", np.ones(m, bool)), ("0270", rng.random(m) < 0.7),
                         ("0320", rng.random(m) < 0.5), ("0360", surg), ("0710", surg), ("0730", rng.random(m) < 0.3)]:
            b.lines(ck[mk], None, np.full(mk.sum(), code), np.ones(mk.sum()), admit[mk])
        # hospitalist professional claim
        ck2 = b.new_ck(m)
        hsp = b.npi(E["state"].values, "hospitalist")
        b.header(E, ck2, "inpatient_professional", "professional", None, np.full(m, "21"), b.npi(E["state"].values, "group"),
                 hsp, admit, disch, prim, sec)
        b.lines(ck2, ch(rng, ["99222", "99223"], m, [0.4, 0.6]), None, np.ones(m), admit)
        mid = los >= 2
        b.lines(ck2[mid], ch(rng, ["99232", "99233"], mid.sum(), [0.7, 0.3]), None, (los - 1)[mid],
                (admit + 1)[mid] if mid.any() else admit[mid])
        b.lines(ck2, np.full(m, "99238"), None, np.ones(m), disch)
        # surgeon / OB claim
        sp = np.isin(drg, ["470", "788", "807"])
        if sp.any():
            Es = E[sp].reset_index(drop=True)
            k = sp.sum()
            ck3 = b.new_ck(k)
            cpt = np.array([{"470": "27447", "788": "59510", "807": "59400"}[d] for d in drg[sp]], dtype=object)
            surgeon = np.where(drg[sp] == "470", b.npi(Es["state"].values, "ortho"), b.npi(Es["state"].values, "obgyn"))
            b.header(Es, ck3, "surgery_professional", "professional", None, np.full(k, "21"), surgeon, surgeon,
                     admit[sp], disch[sp], prim[sp], sec[sp])
            b.lines(ck3, cpt, None, np.ones(k), admit[sp])
        # auths: elective + maternity notification, some urgent notifications
        need = np.isin(drg, ["470", "788", "807"]) | (rng.random(m) < 0.4)
        urg = np.where(np.isin(drg, ["470"]), "standard", "expedited")
        b.need_auth(E[need], ck[need], hosp[need], np.full(need.sum(), "Inpatient Admission"),
                    np.full(need.sum(), None, dtype=object), admit[need], urg[need])

    # 6. outpatient surgery -----------------------------------------------------
    E = events(rng, mm, 0.0035 * agef * np.sqrt(r))
    m = len(E)
    if m:
        cpt = ch(rng, ["45378", "45380", "29881", "47562", "66984", "27447"], m, [.25, .15, .20, .15, .15, .10])
        cpt[np.isin(cpt, ["45378", "45380"]) & (E["age_m"].values < 45)] = "29881"
        cpt[(cpt == "66984") & (E["age_m"].values < 55)] = "47562"
        cpt[(cpt == "27447") & (E["age_m"].values < 55)] = "29881"
        dxm = {"45378": "Z12.11", "45380": "Z12.11", "29881": "M25.561", "47562": "K80.20", "66984": "H25.9", "27447": "M17.11"}
        prim = np.array([dxm[c] for c in cpt], dtype=object)
        sec = drop_code(E["chronic_codes"].values, prim)
        grp = np.array([{"45378": "gastro", "45380": "gastro", "29881": "ortho", "47562": "gensurg", "66984": "ophth",
                         "27447": "ortho"}[c] for c in cpt], dtype=object)
        surgeon = np.empty(m, dtype=object)
        for g in np.unique(grp):
            mk = grp == g
            surgeon[mk] = b.npi(E["state"].values[mk], g)
        hospital_op = rng.random(m) < 0.40
        ckf = b.new_ck(m)
        fac = np.where(hospital_op, b.npi(E["state"].values, "hospital"), b.npi(E["state"].values, "asc"))
        b.header(E, ckf, "op_surgery_facility", np.where(hospital_op, "institutional", "professional"),
                 np.where(hospital_op, "0831", None), np.where(hospital_op, None, "24"), fac,
                 np.full(m, None, dtype=object), E["svc"].values, E["svc"].values, prim, sec)
        ho = hospital_op
        b.lines(ckf[ho], cpt[ho], np.full(ho.sum(), "0490"), np.ones(ho.sum()), E["svc"].values[ho])
        b.lines(ckf[ho], None, np.full(ho.sum(), "0710"), np.ones(ho.sum()), E["svc"].values[ho])
        b.lines(ckf[ho], None, np.full(ho.sum(), "0250"), np.ones(ho.sum()), E["svc"].values[ho])
        asc = ~ho
        b.lines(ckf[asc], cpt[asc], None, np.ones(asc.sum()), E["svc"].values[asc],
                base=np.array([PROC[c][2] * 2.2 for c in cpt[asc]]), mod=np.full(asc.sum(), "SG"))
        cks = b.new_ck(m)
        b.header(E, cks, "op_surgery_professional", "professional", None, np.where(hospital_op, "22", "24"), surgeon,
                 surgeon, E["svc"].values, E["svc"].values, prim, sec)
        b.lines(cks, cpt, None, np.ones(m), E["svc"].values)
        need = ~np.isin(cpt, ["45378", "45380"])
        b.need_auth(E[need], ckf[need], surgeon[need], np.full(need.sum(), "Outpatient Surgery"), cpt[need],
                    E["svc"].values[need], np.full(need.sum(), "standard"))

    # 7. physical therapy + 8. behavioral health -------------------------------
    E = events(rng, mm, 0.02 * agef)
    m = len(E)
    if m:
        ck = b.new_ck(m)
        prim = ch(rng, ["M54.50", "M25.561", "S93.401A", "M17.11"], m)
        pt = b.npi(E["state"].values, "pt")
        b.header(E, ck, "therapy", "professional", None, np.full(m, "11"), pt, pt, E["svc"].values, E["svc"].values,
                 prim, drop_code(E["chronic_codes"].values, prim))
        b.lines(ck, np.full(m, "97110"), None, rng.integers(2, 4, m), E["svc"].values)
        mk = rng.random(m) < 0.6
        b.lines(ck[mk], np.full(mk.sum(), "97140"), None, rng.integers(1, 3, mk.sum()), E["svc"].values[mk])
        mk = rng.random(m) < 0.3
        b.lines(ck[mk], np.full(mk.sum(), "97530"), None, np.ones(mk.sum()), E["svc"].values[mk])
    E = events(rng, mm, 0.022 * np.where(mm["lob"].values == "Medicaid", 1.5, 1.0) * (age >= 6))
    m = len(E)
    if m:
        ck = b.new_ck(m)
        prim = ch(rng, ["F41.1", "F32.9"], m)
        ps = b.npi(E["state"].values, "psych")
        b.header(E, ck, "behavioral", "professional", None, ch(rng, ["11", "10"], m, [0.65, 0.35]), ps, ps,
                 E["svc"].values, E["svc"].values, prim, drop_code(E["chronic_codes"].values, prim))
        b.lines(ck, ch(rng, ["90834", "90837", "90791"], m, [.5, .35, .15]), None, np.ones(m), E["svc"].values)

    # 9. preventive visits ------------------------------------------------------
    E = events(rng, mm, np.full(n, 0.045))
    m = len(E)
    if m:
        a = E["age_m"].values
        newp = rng.random(m) < 0.1
        code = np.select(
            [E["lob"].values == "Medicare Advantage", a < 1, a < 5, a < 12, a < 18, a < 40],
            [np.where(newp, "G0438", "G0439"), "99391", "99392", "99393", "99394", np.where(newp, "99385", "99395")],
            np.where(newp, "99386", np.where(a >= 65, "99397", "99396")))
        prim = np.where(a < 18, "Z00.129", ch(rng, ["Z00.00", "Z00.01"], m, [0.7, 0.3])).astype(object)
        ck = b.new_ck(m)
        rend = E["pcp_npi"].values
        b.header(E, ck, "preventive", "professional", None, np.full(m, "11"), rend, rend, E["svc"].values, E["svc"].values,
                 prim, E["chronic_codes"].values)
        b.lines(ck, code, None, np.ones(m), E["svc"].values)
        vac = rng.random(m) < 0.30
        b.lines(ck[vac], ch(rng, ["90686", "90715"], vac.sum()), None, np.ones(vac.sum()), E["svc"].values[vac])
        b.lines(ck[vac], np.full(vac.sum(), "90471"), None, np.ones(vac.sum()), E["svc"].values[vac])

    # 10. oncology infusions (high-cost tail) -----------------------------------
    E = events(rng, mm, 0.85 * mm["oncology"].values)
    m = len(E)
    if m:
        ck = b.new_ck(m)
        onc = b.npi(E["state"].values, "oncology")
        prim = np.full(m, "C50.911", dtype=object)
        b.header(E, ck, "infusion", "professional", None, np.full(m, "22"), b.npi(E["state"].values, "group"), onc,
                 E["svc"].values, E["svc"].values, prim,
                 np.array(["|".join([x for x in ["Z51.11", c] if x]) for c in E["chronic_codes"].values], dtype=object))
        b.lines(ck, np.full(m, "J9271"), None, np.full(m, 200), E["svc"].values)
        b.lines(ck, np.full(m, "96413"), None, np.ones(m), E["svc"].values)
        first = ~E.duplicated("member_idx").values
        b.need_auth(E[first], ck[first], onc[first], np.full(first.sum(), "Specialty Drug"), np.full(first.sum(), "J9271"),
                    E["svc"].values[first], np.full(first.sum(), "standard"))


# ---------------------------------------------------------------------------
def finalize(rng, b, mm_attrs, counters, stats):
    """Price, adjudicate, date, and inject data-quality issues. Returns headers, lines, auths."""
    H = pd.concat(b.H, ignore_index=True)
    L = pd.concat(b.L, ignore_index=True)
    A = pd.concat(b.auth, ignore_index=True) if b.auth else pd.DataFrame()
    attrs = mm_attrs

    # ---- claims outside eligibility (~1%): move service dates outside the member's coverage
    cov = b.coverage  # member_idx -> (min month, max month, set of months)
    pick = np.where(rng.random(len(H)) < 0.01)[0]
    shift = np.zeros(len(H), dtype=int)
    for i in pick:
        lo, hi = cov[H["member_idx"].iat[i]]
        d = H["service_from_date"].values[i].astype("datetime64[D]")
        if hi < 29:
            target = month_start(hi + 1 + int(rng.integers(0, 2))) + int(rng.integers(0, 27))
        elif lo > 0:
            target = month_start(lo - 1) + int(rng.integers(0, 27))
        else:
            continue
        shift[i] = int((target - d).astype(int))
    outside = shift != 0
    for c in ["service_from_date", "service_to_date", "admit_date", "discharge_date"]:
        H[c] = H[c].values + shift.astype("timedelta64[D]")
    line_shift = pd.Series(shift, index=H["ck"].values).reindex(L["ck"].values).values
    L["line_service_date"] = L["line_service_date"].values + line_shift.astype("timedelta64[D]")
    H["outside_elig"] = outside
    stats["claims_outside_eligibility"] += int(outside.sum())

    # ---- auths: outcome per claim requiring one
    auth_ok = pd.Series(True, index=H["ck"])
    if len(A):
        na = len(A)
        has = rng.random(na) < 0.85
        decision = ch(rng, ["approved", "partial", "denied"], na, [0.88, 0.04, 0.08])
        A["has"] = has
        A["decision"] = decision
        bad = A.loc[~has | (decision == "denied"), "ck"]
        auth_ok[bad.values] = False
        A = A[has].copy()

    # ---- pricing
    lob_f = H.set_index("ck")["lob"].map(LOB_FACTOR)
    L["lobf"] = lob_f.reindex(L["ck"]).values
    noise = rng.lognormal(0, 0.15, len(L))
    L["allowed"] = np.round(L["base_unit"].values * L["units"].values * L["lobf"].values * noise, 2)
    # inpatient: DRG payment allocated across facility lines
    ip = H[H["kind"] == "inpatient"].set_index("ck")
    if len(ip):
        pay = np.array([DRG[d][1] for d in ip["drg_code"]]) * DRG_BASE_RATE * ip["lob"].map(LOB_FACTOR).values \
            * rng.lognormal(0, 0.12, len(ip))
        pay = pd.Series(pay, index=ip.index)
        m = L["ck"].isin(ip.index)
        tot = L[m].groupby("ck")["allowed"].transform("sum")
        L.loc[m, "allowed"] = np.round(L.loc[m, "allowed"] / tot * pay.reindex(L.loc[m, "ck"]).values, 2)
    oon = H["billing_npi"].map(b.oon).fillna(False).values.astype(bool)
    L["oon"] = pd.Series(oon, index=H["ck"]).reindex(L["ck"]).values
    L.loc[L["oon"], "allowed"] = np.round(L.loc[L["oon"], "allowed"] * 0.8, 2)
    inst = pd.Series(H["claim_type"].values == "institutional", index=H["ck"]).reindex(L["ck"]).values
    L["billed"] = np.round(L["allowed"] * np.where(inst, rng.uniform(2.5, 4.5, len(L)), rng.uniform(1.6, 3.2, len(L))), 2)

    # ---- dates
    n = len(H)
    u = rng.random(n)
    lag = np.where(u < 0.85, rng.lognormal(np.log(12), 0.6, n),
                   np.where(u < 0.97, rng.uniform(30, 120, n), rng.uniform(120, 540, n))).astype(int)
    H["received_date"] = H["service_to_date"].values + lag.astype("timedelta64[D]")
    keep = H["received_date"].values <= EXTRACT_DATE
    stats["claims_not_yet_received_dropped"] += int((~keep).sum())
    H = H[keep].reset_index(drop=True)
    L = L[L["ck"].isin(H["ck"])].reset_index(drop=True)
    n = len(H)
    recent = H["received_date"].values >= EXTRACT_DATE - 30
    pended = (recent & (rng.random(n) < 0.5)) | (rng.random(n) < 0.004)
    H["adjudicated_date"] = np.where(pended, NAT, H["received_date"].values + rng.integers(1, 25, n).astype("timedelta64[D]"))
    H["adjudicated_date"] = pd.to_datetime(H["adjudicated_date"])
    late_adj = H["adjudicated_date"].values > EXTRACT_DATE
    pended |= late_adj
    H.loc[late_adj, "adjudicated_date"] = NAT

    # ---- adjudication
    den_p = 0.055 + 0.10 * H["billing_npi"].map(b.oon).fillna(False).values.astype(float)
    denied = (~pended) & (rng.random(n) < den_p)
    reason = np.full(n, None, dtype=object)
    reason[denied] = ch(rng, list(DENIAL_WEIGHTS), denied.sum(), list(DENIAL_WEIGHTS.values()))
    no_auth = ~auth_ok.reindex(H["ck"]).fillna(True).values.astype(bool)
    na_den = (~pended) & no_auth & (rng.random(n) < 0.7)
    denied |= na_den
    reason[na_den] = "CO-197"
    oe_den = (~pended) & H["outside_elig"].values & (rng.random(n) < 0.5)
    denied |= oe_den
    reason[oe_den] = "CO-27"
    status = np.where(pended, "pended", np.where(denied, "denied", "paid")).astype(object)
    H["claim_status"] = status
    H["denial_reason_code"] = reason
    H["paid_date"] = np.where(status == "paid", H["adjudicated_date"].values + rng.integers(0, 10, n).astype("timedelta64[D]"), NAT)
    H["paid_date"] = pd.to_datetime(H["paid_date"])

    st_line = pd.Series(status, index=H["ck"]).reindex(L["ck"]).values
    L.loc[st_line != "paid", "allowed"] = 0.0
    lob_line = H.set_index("ck")["lob"].reindex(L["ck"]).values
    kind_line = H.set_index("ck")["kind"].reindex(L["ck"]).values
    rate = np.select([lob_line == "Medicaid", lob_line == "Medicare Advantage"], [0.0, 0.10], 0.20)
    rate = np.where(kind_line == "preventive", 0.0, rate)
    rate = np.where((kind_line == "office") & (lob_line == "Commercial"), 0.0, rate)
    L["member_resp"] = np.round(L["allowed"] * rate, 2)
    # commercial office copay $30 on the E&M line
    cop = (kind_line == "office") & (lob_line == "Commercial") & (L["procedure_code"].astype(str).str.startswith("992").values) & (st_line == "paid")
    L.loc[cop, "member_resp"] = np.minimum(30.0, L.loc[cop, "allowed"])
    L["paid"] = np.round(L["allowed"] - L["member_resp"], 2)

    # ---- ids & frequency codes
    H = H.sort_values("received_date", kind="stable").reset_index(drop=True)
    start = counters["claim"]
    H["claim_id"] = [f"CLM{start + i:011d}" for i in range(len(H))]
    counters["claim"] += len(H)
    H["claim_frequency_code"] = "1"
    H["original_claim_id"] = None
    cid = H.set_index("ck")["claim_id"]
    L["claim_id"] = cid.reindex(L["ck"]).values
    L = L.sort_values(["claim_id", "line_service_date"], kind="stable")
    L["line_number"] = L.groupby("claim_id").cumcount() + 1

    # ---- adjustments: replacements (freq 7) and voids (freq 8), ~6% of paid claims
    elig = H[(H["claim_status"] == "paid") & (H["adjudicated_date"] <= EXTRACT_DATE - 20)]
    adj = elig.sample(frac=min(1.0, 0.06 * len(H) / max(len(elig), 1)), random_state=int(rng.integers(1e9)))
    kinds = ch(rng, ["replace", "replace2", "void"], len(adj), [0.70, 0.15, 0.15])
    newH, newL = [], []
    adj_lines = {k: g for k, g in L[L["ck"].isin(adj["ck"])].groupby("ck")}
    for (_, row), kd in zip(adj.iterrows(), kinds):
        prev = row
        prev_lines = adj_lines[row["ck"]]
        steps = ["replace", "replace"] if kd == "replace2" else [kd]
        for stp in steps:
            rec = prev["adjudicated_date"] + np.timedelta64(int(rng.integers(10, 90)), "D")
            if rec > EXTRACT_DATE:
                break
            adjd = rec + np.timedelta64(int(rng.integers(1, 15)), "D")
            if adjd > EXTRACT_DATE:
                break
            h = prev.copy()
            h["claim_id"] = f"CLM{counters['claim']:011d}"
            counters["claim"] += 1
            h["original_claim_id"] = prev["claim_id"]
            h["received_date"], h["adjudicated_date"] = rec, adjd
            h["paid_date"] = adjd + np.timedelta64(int(rng.integers(0, 10)), "D")
            ln = prev_lines.copy()
            ln["claim_id"] = h["claim_id"]
            if stp == "void":
                h["claim_frequency_code"], h["claim_status"] = "8", "void"
                for c in ["billed", "allowed", "member_resp", "paid"]:
                    ln[c] = -ln[c]
            else:
                h["claim_frequency_code"] = "7"
                f = rng.uniform(0.85, 1.15)
                ln["allowed"] = np.round(ln["allowed"] * f, 2)
                ln["member_resp"] = np.round(ln["member_resp"] * f, 2)
                ln["paid"] = np.round(ln["allowed"] - ln["member_resp"], 2)
            newH.append(h)
            newL.append(ln)
            prev, prev_lines = h, ln
            stats[f"adjustment_{'void' if stp == 'void' else 'replacement'}_rows"] += 1
    if newH:
        H = pd.concat([H, pd.DataFrame(newH)], ignore_index=True)
        L = pd.concat([L] + newL, ignore_index=True)

    # ---- header totals
    tot = L.groupby("claim_id")[["billed", "allowed", "paid", "member_resp"]].sum().round(2)
    H = H.merge(tot, left_on="claim_id", right_index=True, how="left")
    H = H.rename(columns={"billed": "total_billed_amt", "allowed": "total_allowed_amt", "paid": "total_paid_amt",
                          "member_resp": "member_responsibility_amt"})

    # ---- data-quality injection ------------------------------------------------
    n = len(H)
    mis = np.where((rng.random(n) < 0.005) & (H["total_paid_amt"].values > 0))[0]
    H.loc[H.index[mis], "total_paid_amt"] = np.round(H["total_paid_amt"].values[mis] + rng.choice([-1, 1], len(mis))
                                                     * rng.uniform(1, 50, len(mis)), 2)
    stats["header_line_paid_mismatch"] += len(mis)

    H["member_id"] = attrs["member_id"].values[H["member_idx"].values]
    orph = rng.random(n) < 0.003
    H.loc[orph, "member_id"] = [f"PCH9{rng.integers(0, 10**8):08d}" for _ in range(orph.sum())]
    stats["orphan_member_claims"] += int(orph.sum())
    onpi = rng.random(n) < 0.005
    fake_npi = np.array([f"1999{rng.integers(0, 10**6):06d}" for _ in range(onpi.sum())], dtype=object)
    has_r = H["rendering_npi"].notna().values
    H.loc[onpi & has_r, "rendering_npi"] = fake_npi[has_r[onpi]]
    H.loc[onpi & ~has_r, "billing_npi"] = fake_npi[~has_r[onpi]]
    stats["orphan_npi_claims"] += int(onpi.sum())

    fut = np.where(rng.random(n) < 0.0002)[0]
    H.loc[H.index[fut], "service_from_date"] = (np.datetime64("2027-01-01") + rng.integers(0, 300, len(fut)).astype("timedelta64[D]"))
    stats["future_service_dates"] += len(fut)
    neg = np.where((rng.random(n) < 0.0002) & (H["total_allowed_amt"].values > 0))[0]
    H.loc[H.index[neg], "total_allowed_amt"] = -H["total_allowed_amt"].values[neg]
    stats["negative_allowed_errors"] += len(neg)

    # line-level mess on rendering npi
    r = rng.random(n)
    H.loc[(r < 0.005) & H["rendering_npi"].notna(), "rendering_npi"] = "NULL"
    H.loc[(r >= 0.005) & (r < 0.008) & H["rendering_npi"].notna(), "rendering_npi"] = "N/A"

    # dx columns
    sec = H["sec_dx"].fillna("").str.split("|", expand=True)
    sec = sec.reindex(columns=range(11))
    H["primary_dx_code"] = H["primary_dx_code"].astype(object)
    dx_cols = ["primary_dx_code"]
    for i in range(11):
        col = f"dx_code_{i + 2}"
        H[col] = sec[i].replace("", None).values
        dx_cols.append(col)
    for c in dx_cols:
        s = H[c].astype(object)
        ok = s.notna()
        if not ok.any():
            continue
        u = rng.random(len(s))
        s = s.where(~(ok & (u < 0.25)), s.str.replace(".", "", regex=False))
        s = s.where(~(ok & (u >= 0.25) & (u < 0.28)), s.str.lower())
        s = s.where(~(ok & (u >= 0.28) & (u < 0.30)), s + "  ")
        H[c] = s

    # duplicates (~0.5%), chosen before date formatting so they are exact copies
    dup_ids = H["claim_id"].values[rng.random(n) < 0.005]
    stats["duplicate_header_rows"] += len(dup_ids)
    return H, L, A, set(dup_ids)


def format_dates(H, L, rng):
    def iso(s):
        s = pd.to_datetime(pd.Series(s))
        return s.dt.strftime("%Y-%m-%d").where(s.notna(), None)
    for c in ["service_from_date", "service_to_date", "admit_date", "discharge_date", "received_date",
              "adjudicated_date", "paid_date"]:
        H[c] = iso(H[c].values).values
    n = len(H)
    m = rng.random(n) < 0.01
    d = pd.to_datetime(H.loc[m, "service_from_date"])
    H.loc[m, "service_from_date"] = d.dt.strftime("%m/%d/%Y").values
    m = rng.random(n) < 0.01
    d = pd.to_datetime(H.loc[m, "received_date"])
    H.loc[m, "received_date"] = d.dt.strftime("%Y%m%d").values
    L["line_service_date"] = iso(L["line_service_date"].values).values
    return H, L


HEADER_COLS = ["claim_id", "claim_frequency_code", "original_claim_id", "member_id", "billing_npi", "rendering_npi",
               "claim_type", "bill_type", "place_of_service", "admit_date", "discharge_date", "service_from_date",
               "service_to_date", "received_date", "adjudicated_date", "paid_date", "claim_status", "denial_reason_code",
               "total_billed_amt", "total_allowed_amt", "total_paid_amt", "member_responsibility_amt",
               "primary_dx_code"] + [f"dx_code_{i}" for i in range(2, 13)] + ["drg_code"]
LINE_COLS = ["claim_id", "line_number", "procedure_code", "modifier_1", "modifier_2", "revenue_code", "units",
             "line_billed_amt", "line_allowed_amt", "line_paid_amt", "line_service_date"]


def shape_lines(L):
    L = L.rename(columns={"billed": "line_billed_amt", "allowed": "line_allowed_amt", "paid": "line_paid_amt"})
    L["modifier_2"] = None
    return L[LINE_COLS]


def build_auths(rng, A, H, attrs, counters, stats, lut):
    """Auth requests for services that needed one, plus denied requests that never became claims."""
    if not len(A):
        return pd.DataFrame()
    n = len(A)
    exp = A["urgency"].values == "expedited"
    lead = np.where(exp, rng.integers(0, 3, n), rng.integers(3, 22, n))
    req = A["service_date"].values - lead.astype("timedelta64[D]")
    dec = req + np.where(exp, rng.integers(0, 2, n), rng.integers(1, 14, n)).astype("timedelta64[D]")
    out = pd.DataFrame({
        "member_id": attrs["member_id"].values[A["member_idx"].values], "requesting_npi": A["requesting_npi"].values,
        "service_type": A["service_type"].values, "procedure_code": A["procedure_code"].values,
        "request_date": req, "decision_date": dec, "decision": A["decision"].values, "urgency": A["urgency"].values,
    })
    # denied requests with no downstream claim (~15% extra)
    k = int(n * 0.15)
    src = out.sample(k, replace=True, random_state=int(rng.integers(1e9))).copy()
    src["decision"] = "denied"
    shift = rng.integers(-60, 60, k).astype("timedelta64[D]")
    src["request_date"] = src["request_date"].values + shift
    src["decision_date"] = src["decision_date"].values + shift
    out = pd.concat([out, src], ignore_index=True)
    out = out[out["request_date"] <= EXTRACT_DATE].copy()
    pend = out["decision_date"].values > EXTRACT_DATE
    out.loc[pend, "decision"] = None
    out.loc[pend, "decision_date"] = NAT
    out = out.sort_values("request_date").reset_index(drop=True)
    out.insert(0, "auth_id", [f"PA{counters['auth'] + i:010d}" for i in range(len(out))])
    counters["auth"] += len(out)
    for c in ["request_date", "decision_date"]:
        s = pd.to_datetime(out[c])
        out[c] = s.dt.strftime("%Y-%m-%d").where(s.notna(), None)
    stats["auths_without_claim"] += k
    return out
