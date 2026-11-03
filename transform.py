from datetime import datetime

# Age unit codes -> multiply to get years
AGE_UNITS = {"800": 10, "801": 1, "802": 1/12, "803": 1/52,
             "804": 1/365, "805": 1/8760}
SEX = {"1": "M", "2": "F"}
KEEP_ROLES = {1, 3}   # 1 = suspect, 3 = interacting

# Reactions that describe HOW a drug was used, not a side effect
NOISE = {"OFF LABEL USE", "DRUG INEFFECTIVE", "NO ADVERSE EVENT",
         "INAPPROPRIATE SCHEDULE OF PRODUCT ADMINISTRATION",
         "WRONG TECHNIQUE IN PRODUCT USAGE PROCESS",
         "INTENTIONAL PRODUCT USE ISSUE", "DRUG DOSE OMISSION"}

def is_noise(term):
    return term in NOISE or term.startswith("PRODUCT ")

def to_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None

def age_in_years(patient):
    age = patient.get("patientonsetage")
    mult = AGE_UNITS.get(patient.get("patientonsetageunit"))
    try:
        years = round(float(age) * mult, 1)
    except (TypeError, ValueError):
        return None
    return years if 0 <= years <= 120 else None

def transform(raw_reports):
    reports, drugs, reactions = {}, [], []

    # If the same report appears twice, keep the latest version
    latest = {}
    for r in raw_reports:
        rid = r["safetyreportid"]
        if rid not in latest or to_int(r.get("safetyreportversion")) > to_int(latest[rid].get("safetyreportversion")):
            latest[rid] = r

    for rid, r in latest.items():
        p = r.get("patient", {})
        reports[rid] = {
            "safetyreportid": rid,
            "report_version": to_int(r.get("safetyreportversion")),
            "receive_date": datetime.strptime(r["receivedate"], "%Y%m%d").date(),
            "serious": r.get("serious") == "1",
            "death": r.get("seriousnessdeath") == "1",
            "hospitalization": r.get("seriousnesshospitalization") == "1",
            "life_threatening": r.get("seriousnesslifethreatening") == "1",
            "country": r.get("occurcountry"),
            "reporter_type": to_int((r.get("primarysource") or {}).get("qualification")),
            "patient_age_years": age_in_years(p),
            "patient_sex": SEX.get(p.get("patientsex")),
        }

        seen = set()
        for d in p.get("drug", []):
            role = to_int(d.get("drugcharacterization"))
            if role not in KEEP_ROLES:
                continue
            product = (d.get("medicinalproduct") or "").strip().upper() or None
            generic_list = (d.get("openfda") or {}).get("generic_name") or []
            generic = generic_list[0].strip().upper() if generic_list else None
            key = (generic or product, role)
            if key in seen:
                continue
            seen.add(key)
            drugs.append({"safetyreportid": rid, "product_name": product,
                          "generic_name": generic, "drug_role": role})

        seen = set()
        for rx in p.get("reaction", []):
            term = (rx.get("reactionmeddrapt") or "").strip().upper()
            if not term or is_noise(term) or term in seen:
                continue
            seen.add(term)
            reactions.append({"safetyreportid": rid, "reaction": term,
                              "outcome": to_int(rx.get("reactionoutcome"))})

    return list(reports.values()), drugs, reactions

if __name__ == "__main__":
    import pandas as pd
    from extract import fetch_day

    raw = fetch_day("20250115")
    reps, drgs, rxns = transform(raw)
    print(f"Raw: {len(raw)} | Reports: {len(reps)} | Drugs: {len(drgs)} | Reactions: {len(rxns)}")
    print("\nSample reports:\n", pd.DataFrame(reps).head())
    print("\nTop suspect drugs:\n", pd.DataFrame(drgs)["generic_name"].value_counts().head(10))
    print("\nTop reactions (noise removed):\n", pd.DataFrame(rxns)["reaction"].value_counts().head(10))