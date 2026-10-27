"""Reference data for the Pacific Crest Health synthetic generator.

Code lists are a curated, realistic subset (not full code sets). Prices are
illustrative allowed amounts before line-of-business adjustment.
"""

# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------
STATES = {
    "CA": {"weight": 0.60, "counties": [
        ("Los Angeles", ["Los Angeles", "Long Beach", "Pasadena", "Glendale", "Torrance"], "900"),
        ("Orange", ["Irvine", "Anaheim", "Santa Ana", "Huntington Beach", "Fullerton"], "926"),
        ("San Diego", ["San Diego", "Chula Vista", "Oceanside", "Escondido"], "921"),
        ("Riverside", ["Riverside", "Moreno Valley", "Temecula", "Corona"], "925"),
        ("Sacramento", ["Sacramento", "Elk Grove", "Folsom"], "958"),
        ("Fresno", ["Fresno", "Clovis"], "937"),
    ]},
    "NV": {"weight": 0.20, "counties": [
        ("Clark", ["Las Vegas", "Henderson", "North Las Vegas"], "891"),
        ("Washoe", ["Reno", "Sparks"], "895"),
    ]},
    "AZ": {"weight": 0.20, "counties": [
        ("Maricopa", ["Phoenix", "Mesa", "Scottsdale", "Chandler", "Tempe"], "850"),
        ("Pima", ["Tucson", "Marana"], "857"),
    ]},
}

LANGUAGES = [("ENG", 0.70), ("SPA", 0.22), ("VIE", 0.03), ("CHI", 0.02), ("TGL", 0.02), ("KOR", 0.01)]
RACE_ETH = [("WH", 0.36), ("HI", 0.34), ("AS", 0.12), ("BL", 0.09), ("AI", 0.02), ("PI", 0.01), ("OT", 0.03), ("UN", 0.03)]

# ---------------------------------------------------------------------------
# Plans: (plan_id, plan_name, lob, metal_tier, state, deductible, oop_max)
# ---------------------------------------------------------------------------
def build_plans():
    rows = []
    for st in ["CA", "NV", "AZ"]:
        rows.append((f"MCD-{st}-01", f"Pacific Crest Medicaid {st}", "Medicaid", None, st, 0, 0))
        rows.append((f"MA-{st}-HMO", f"Pacific Crest Medicare Advantage HMO {st}", "Medicare Advantage", None, st, 0, 4900))
        rows.append((f"MA-{st}-PPO", f"Pacific Crest Medicare Advantage PPO {st}", "Medicare Advantage", None, st, 250, 6700))
        for tier, ded, oop in [("Bronze", 7500, 9200), ("Silver", 4500, 8500), ("Gold", 1500, 6000), ("Platinum", 250, 3000)]:
            rows.append((f"COM-{st}-{tier[:3].upper()}", f"Pacific Crest {tier} {st}", "Commercial", tier, st, ded, oop))
    return rows

COVERAGE_TIERS_COMMERCIAL = [("EE", 0.45), ("ES", 0.15), ("EC", 0.15), ("FAM", 0.25)]

# ---------------------------------------------------------------------------
# Providers: specialty group -> list of (taxonomy code, description), share of providers, is_org
# ---------------------------------------------------------------------------
SPECIALTIES = {
    "pcp": ([("207Q00000X", "Family Medicine"), ("207R00000X", "Internal Medicine"),
             ("208000000X", "Pediatrics"), ("363L00000X", "Nurse Practitioner")], 0.28, False),
    "er_doc": ([("207P00000X", "Emergency Medicine")], 0.06, False),
    "hospitalist": ([("208M00000X", "Hospitalist")], 0.05, False),
    "radiology": ([("2085R0202X", "Diagnostic Radiology")], 0.05, False),
    "cardiology": ([("207RC0000X", "Cardiovascular Disease")], 0.04, False),
    "endo": ([("207RE0101X", "Endocrinology, Diabetes & Metabolism")], 0.02, False),
    "pulm": ([("207RP1001X", "Pulmonary Disease")], 0.02, False),
    "ortho": ([("207X00000X", "Orthopaedic Surgery")], 0.04, False),
    "gensurg": ([("208600000X", "Surgery")], 0.04, False),
    "obgyn": ([("207V00000X", "Obstetrics & Gynecology")], 0.04, False),
    "ophth": ([("207W00000X", "Ophthalmology")], 0.02, False),
    "gastro": ([("207RG0100X", "Gastroenterology")], 0.02, False),
    "oncology": ([("207RX0202X", "Medical Oncology")], 0.015, False),
    "psych": ([("2084P0800X", "Psychiatry"), ("103T00000X", "Psychologist"), ("1041C0700X", "Clinical Social Worker")], 0.06, False),
    "pt": ([("225100000X", "Physical Therapist")], 0.05, False),
    "group": ([("193200000X", "Multi-Specialty Group")], 0.08, True),
    "hospital": ([("282N00000X", "General Acute Care Hospital")], 0.03, True),
    "asc": ([("261QA1903X", "Ambulatory Surgical Center")], 0.02, True),
    "lab": ([("291U00000X", "Clinical Medical Laboratory")], 0.02, True),
    "imaging_center": ([("261QR0200X", "Radiology Clinic/Center")], 0.015, True),
    "ambulance": ([("3416A0800X", "Air/Ground Ambulance")], 0.01, True),
}

ORG_NAME_PARTS = {
    "hospital": (["Sierra Vista", "Mission Valley", "Desert Springs", "Harbor View", "Golden Hills", "Canyon Ridge",
                  "Bayside", "Saguaro", "Redwood", "Silver State", "Coastal", "Valley Oaks"],
                 ["Medical Center", "Regional Hospital", "Community Hospital", "Memorial Hospital"]),
    "group": (["Summit", "Pinnacle", "Horizon", "Evergreen", "Meridian", "Crestline", "Lakeside", "Northstar"],
              ["Medical Group", "Physicians Group", "Health Partners", "Family Medical Associates"]),
    "asc": (["Pacific", "Mesa", "Foothill", "Seaside", "Sunrise"], ["Surgery Center", "Ambulatory Surgery Center"]),
    "lab": (["Precision", "Western", "Accurate", "ClearPath", "Sonoran"], ["Diagnostic Labs", "Clinical Laboratory"]),
    "imaging_center": (["Pacific", "Valley", "Desert", "Advanced"], ["Imaging", "Open MRI & Imaging"]),
    "ambulance": (["Rapid", "Lifeline", "Guardian", "Frontier"], ["Ambulance Service", "EMS"]),
}

# ---------------------------------------------------------------------------
# Diagnosis codes (canonical with decimal) -> (description, chronic condition or None)
# ---------------------------------------------------------------------------
DX = {
    "E11.9": ("Type 2 diabetes mellitus without complications", "diabetes"),
    "E11.65": ("Type 2 diabetes mellitus with hyperglycemia", "diabetes"),
    "E11.22": ("Type 2 diabetes mellitus with diabetic chronic kidney disease", "diabetes"),
    "E11.40": ("Type 2 diabetes mellitus with diabetic neuropathy, unspecified", "diabetes"),
    "E10.9": ("Type 1 diabetes mellitus without complications", "diabetes"),
    "I10": ("Essential (primary) hypertension", "hypertension"),
    "I11.9": ("Hypertensive heart disease without heart failure", "hypertension"),
    "J45.909": ("Unspecified asthma, uncomplicated", "asthma"),
    "J45.20": ("Mild intermittent asthma, uncomplicated", "asthma"),
    "J45.40": ("Moderate persistent asthma, uncomplicated", "asthma"),
    "J45.901": ("Unspecified asthma with (acute) exacerbation", "asthma"),
    "I50.9": ("Heart failure, unspecified", "chf"),
    "I50.22": ("Chronic systolic (congestive) heart failure", "chf"),
    "I50.23": ("Acute on chronic systolic (congestive) heart failure", "chf"),
    "I50.32": ("Chronic diastolic (congestive) heart failure", "chf"),
    "E78.5": ("Hyperlipidemia, unspecified", None),
    "E66.9": ("Obesity, unspecified", None),
    "N18.30": ("Chronic kidney disease, stage 3 unspecified", None),
    "I25.10": ("Atherosclerotic heart disease of native coronary artery", None),
    "E03.9": ("Hypothyroidism, unspecified", None),
    "Z79.4": ("Long term (current) use of insulin", None),
    "J06.9": ("Acute upper respiratory infection, unspecified", None),
    "J02.9": ("Acute pharyngitis, unspecified", None),
    "J20.9": ("Acute bronchitis, unspecified", None),
    "J18.9": ("Pneumonia, unspecified organism", None),
    "J01.90": ("Acute sinusitis, unspecified", None),
    "J10.1": ("Influenza with other respiratory manifestations", None),
    "U07.1": ("COVID-19", None),
    "H66.90": ("Otitis media, unspecified", None),
    "H10.9": ("Unspecified conjunctivitis", None),
    "H25.9": ("Unspecified age-related cataract", None),
    "N39.0": ("Urinary tract infection, site not specified", None),
    "R10.9": ("Unspecified abdominal pain", None),
    "R07.9": ("Chest pain, unspecified", None),
    "R51.9": ("Headache, unspecified", None),
    "R05.9": ("Cough, unspecified", None),
    "R50.9": ("Fever, unspecified", None),
    "R11.2": ("Nausea with vomiting, unspecified", None),
    "R53.83": ("Other fatigue", None),
    "M54.50": ("Low back pain, unspecified", None),
    "M25.561": ("Pain in right knee", None),
    "M17.11": ("Unilateral primary osteoarthritis, right knee", None),
    "M79.10": ("Myalgia, unspecified site", None),
    "S93.401A": ("Sprain of unspecified ligament of right ankle, initial encounter", None),
    "S61.419A": ("Laceration without foreign body of right hand, initial encounter", None),
    "S09.90XA": ("Unspecified injury of head, initial encounter", None),
    "K21.9": ("Gastro-esophageal reflux disease without esophagitis", None),
    "K52.9": ("Noninfective gastroenteritis and colitis, unspecified", None),
    "K80.20": ("Calculus of gallbladder without obstruction", None),
    "L03.115": ("Cellulitis of right lower limb", None),
    "B34.9": ("Viral infection, unspecified", None),
    "A41.9": ("Sepsis, unspecified organism", None),
    "F41.1": ("Generalized anxiety disorder", None),
    "F32.9": ("Major depressive disorder, single episode, unspecified", None),
    "F20.9": ("Schizophrenia, unspecified", None),
    "G43.909": ("Migraine, unspecified", None),
    "C50.911": ("Malignant neoplasm of unspecified site of right female breast", None),
    "Z51.11": ("Encounter for antineoplastic chemotherapy", None),
    "Z00.00": ("Encounter for general adult medical exam without abnormal findings", None),
    "Z00.01": ("Encounter for general adult medical exam with abnormal findings", None),
    "Z00.129": ("Encounter for routine child health exam without abnormal findings", None),
    "Z23": ("Encounter for immunization", None),
    "Z12.31": ("Encounter for screening mammogram for malignant neoplasm of breast", None),
    "Z12.11": ("Encounter for screening for malignant neoplasm of colon", None),
    "Z34.90": ("Encounter for supervision of normal pregnancy, unspecified", None),
    "O80": ("Encounter for full-term uncomplicated delivery", None),
    "O82": ("Encounter for cesarean delivery without indication", None),
}

CHRONIC_DX = {
    "diabetes": (["E11.9", "E11.65", "E11.22", "E11.40", "E10.9"], [0.50, 0.25, 0.10, 0.10, 0.05]),
    "hypertension": (["I10", "I11.9"], [0.85, 0.15]),
    "asthma": (["J45.909", "J45.20", "J45.40"], [0.50, 0.30, 0.20]),
    "chf": (["I50.9", "I50.22", "I50.32"], [0.40, 0.35, 0.25]),
}

ACUTE_OFFICE_DX = ["J06.9", "J02.9", "J20.9", "J01.90", "H66.90", "H10.9", "N39.0", "R10.9", "R51.9", "R05.9",
                   "M54.50", "M25.561", "M79.10", "K21.9", "R53.83", "B34.9", "G43.909", "E78.5", "E66.9", "E03.9"]
ER_DX = ["J06.9", "R07.9", "R10.9", "S93.401A", "S61.419A", "S09.90XA", "R51.9", "J18.9", "N39.0", "L03.115",
         "R50.9", "J10.1", "U07.1", "R11.2", "K52.9"]
RESPIRATORY_ER_DX = ["J06.9", "J18.9", "J10.1", "U07.1", "R05.9", "R50.9", "J20.9"]

# ---------------------------------------------------------------------------
# Procedure codes: code -> (description, category, base allowed)
# ---------------------------------------------------------------------------
PROC = {
    "99202": ("Office visit, new patient, straightforward", "E&M", 75), "99203": ("Office visit, new patient, low", "E&M", 110),
    "99204": ("Office visit, new patient, moderate", "E&M", 165), "99205": ("Office visit, new patient, high", "E&M", 210),
    "99211": ("Office visit, established, minimal", "E&M", 25), "99212": ("Office visit, established, straightforward", "E&M", 55),
    "99213": ("Office visit, established, low", "E&M", 90), "99214": ("Office visit, established, moderate", "E&M", 130),
    "99215": ("Office visit, established, high", "E&M", 180),
    "99281": ("Emergency dept visit, minimal", "ER", 25), "99282": ("Emergency dept visit, straightforward", "ER", 45),
    "99283": ("Emergency dept visit, low", "ER", 75), "99284": ("Emergency dept visit, moderate", "ER", 130),
    "99285": ("Emergency dept visit, high", "ER", 190),
    "99221": ("Initial hospital care, low", "Inpatient Visit", 105), "99222": ("Initial hospital care, moderate", "Inpatient Visit", 140),
    "99223": ("Initial hospital care, high", "Inpatient Visit", 205), "99231": ("Subsequent hospital care, low", "Inpatient Visit", 40),
    "99232": ("Subsequent hospital care, moderate", "Inpatient Visit", 75), "99233": ("Subsequent hospital care, high", "Inpatient Visit", 110),
    "99238": ("Hospital discharge day management", "Inpatient Visit", 75),
    "99385": ("Preventive visit, new, 18-39", "Preventive", 130), "99386": ("Preventive visit, new, 40-64", "Preventive", 150),
    "99391": ("Preventive visit, established, infant", "Preventive", 100), "99392": ("Preventive visit, established, 1-4", "Preventive", 110),
    "99393": ("Preventive visit, established, 5-11", "Preventive", 110), "99394": ("Preventive visit, established, 12-17", "Preventive", 120),
    "99395": ("Preventive visit, established, 18-39", "Preventive", 120), "99396": ("Preventive visit, established, 40-64", "Preventive", 130),
    "99397": ("Preventive visit, established, 65+", "Preventive", 140),
    "G0438": ("Annual wellness visit, initial", "Preventive", 170), "G0439": ("Annual wellness visit, subsequent", "Preventive", 115),
    "36415": ("Routine venipuncture", "Lab", 3), "80053": ("Comprehensive metabolic panel", "Lab", 11),
    "85025": ("Complete blood count with differential", "Lab", 8), "83036": ("Hemoglobin A1c", "Lab", 10),
    "83037": ("Hemoglobin A1c, home device", "Lab", 13), "80061": ("Lipid panel", "Lab", 14),
    "81001": ("Urinalysis with microscopy", "Lab", 3), "87880": ("Strep A antigen test", "Lab", 13),
    "84443": ("Thyroid stimulating hormone", "Lab", 18), "87804": ("Influenza antigen test", "Lab", 13),
    "71045": ("Chest x-ray, single view", "Imaging", 25), "71046": ("Chest x-ray, 2 views", "Imaging", 32),
    "72148": ("MRI lumbar spine without contrast", "Imaging", 220), "73721": ("MRI lower extremity joint without contrast", "Imaging", 210),
    "74177": ("CT abdomen and pelvis with contrast", "Imaging", 320), "70450": ("CT head without contrast", "Imaging", 110),
    "77067": ("Screening mammography, bilateral", "Imaging", 130), "93000": ("Electrocardiogram, complete", "Imaging", 17),
    "93306": ("Echocardiography, complete", "Imaging", 210), "76805": ("Obstetric ultrasound", "Imaging", 120),
    "29881": ("Knee arthroscopy with meniscectomy", "Surgery", 520), "47562": ("Laparoscopic cholecystectomy", "Surgery", 650),
    "27447": ("Total knee arthroplasty", "Surgery", 1350), "66984": ("Cataract removal with lens insertion", "Surgery", 560),
    "45378": ("Diagnostic colonoscopy", "Surgery", 210), "45380": ("Colonoscopy with biopsy", "Surgery", 260),
    "59400": ("Routine obstetric care, vaginal delivery", "Surgery", 2100), "59510": ("Routine obstetric care, cesarean delivery", "Surgery", 2400),
    "97110": ("Therapeutic exercise, 15 min", "Therapy", 30), "97140": ("Manual therapy, 15 min", "Therapy", 28),
    "97530": ("Therapeutic activities, 15 min", "Therapy", 32),
    "90791": ("Psychiatric diagnostic evaluation", "Behavioral Health", 150), "90834": ("Psychotherapy, 45 min", "Behavioral Health", 85),
    "90837": ("Psychotherapy, 60 min", "Behavioral Health", 120),
    "90686": ("Influenza vaccine, quadrivalent", "Vaccine", 20), "90471": ("Immunization administration", "Vaccine", 20),
    "90715": ("Tdap vaccine", "Vaccine", 35),
    "J1100": ("Injection, dexamethasone, 1 mg", "Medical Drug", 1), "J1885": ("Injection, ketorolac, 15 mg", "Medical Drug", 1),
    "J2405": ("Injection, ondansetron, 1 mg", "Medical Drug", 1), "J9271": ("Injection, pembrolizumab, 1 mg", "Medical Drug", 48),
    "96413": ("Chemotherapy IV infusion, first hour", "Medical Drug", 140),
    "A0427": ("Ambulance, advanced life support, emergency", "Transport", 450),
    "A0425": ("Ground mileage, per statute mile", "Transport", 8),
}

# Revenue codes: code -> (description, base allowed per unit)
REV = {
    "0120": ("Room & board, semi-private", 2200), "0250": ("Pharmacy, general", 300), "0270": ("Medical/surgical supplies", 150),
    "0300": ("Laboratory, general", 180), "0320": ("Radiology, diagnostic", 250), "0350": ("CT scan", 450),
    "0360": ("Operating room services", 3500), "0450": ("Emergency room, general", 650), "0490": ("Ambulatory surgical care", 1800),
    "0636": ("Drugs requiring detailed coding", 400), "0710": ("Recovery room", 600), "0730": ("EKG/ECG", 90),
}
ER_REV_CODES = ["0450", "0451", "0452", "0456", "0459"]
REV.update({"0451": ("Emergency room, EMTALA screening", 300), "0452": ("Emergency room, ER beyond EMTALA", 700),
            "0456": ("Emergency room, urgent care", 250), "0459": ("Emergency room, other", 500)})

# DRGs: code -> (description, weight, mean LOS, surgical, primary dx, maternity)
DRG = {
    "291": ("Heart failure and shock with MCC", 1.35, 4.5, False, "I50.23", False),
    "194": ("Simple pneumonia and pleurisy with CC", 0.95, 3.5, False, "J18.9", False),
    "871": ("Septicemia without MV >96 hours with MCC", 1.85, 5.5, False, "A41.9", False),
    "470": ("Major hip and knee joint replacement without MCC", 1.90, 2.0, True, "M17.11", False),
    "392": ("Esophagitis, gastroenteritis and misc digestive disorders without MCC", 0.75, 2.8, False, "K52.9", False),
    "638": ("Diabetes with CC", 0.85, 3.2, False, "E11.65", False),
    "202": ("Bronchitis and asthma with CC/MCC", 0.90, 3.0, False, "J45.901", False),
    "690": ("Kidney and urinary tract infections without MCC", 0.80, 3.0, False, "N39.0", False),
    "313": ("Chest pain", 0.60, 1.5, False, "R07.9", False),
    "885": ("Psychoses", 1.25, 7.0, False, "F20.9", False),
    "807": ("Vaginal delivery without sterilization/D&C without CC/MCC", 0.60, 2.0, False, "O80", True),
    "788": ("Cesarean section without sterilization without CC/MCC", 0.95, 2.8, True, "O82", True),
}
DRG_BASE_RATE = 7800

POS = {
    "02": "Telehealth provided other than in patient's home", "10": "Telehealth provided in patient's home",
    "11": "Office", "12": "Home", "19": "Off campus-outpatient hospital", "20": "Urgent care facility",
    "21": "Inpatient hospital", "22": "On campus-outpatient hospital", "23": "Emergency room - hospital",
    "24": "Ambulatory surgical center", "41": "Ambulance - land", "81": "Independent laboratory",
}

DENIALS = {
    "CO-16": ("Claim lacks information needed for adjudication", "Administrative"),
    "CO-18": ("Exact duplicate claim/service", "Duplicate"),
    "CO-27": ("Expenses incurred after coverage terminated", "Eligibility"),
    "CO-29": ("The time limit for filing has expired", "Timely Filing"),
    "CO-50": ("Non-covered: not deemed a medical necessity", "Clinical"),
    "CO-97": ("Benefit included in payment for another service", "Bundling"),
    "CO-197": ("Precertification/authorization absent", "Authorization"),
    "CO-242": ("Services not provided by network/primary care providers", "Network"),
    "PR-204": ("Service not covered under the patient's current benefit plan", "Benefit"),
}
DENIAL_WEIGHTS = {"CO-16": 0.22, "CO-18": 0.10, "CO-27": 0.06, "CO-29": 0.07, "CO-50": 0.15, "CO-97": 0.14,
                  "CO-197": 0.12, "CO-242": 0.08, "PR-204": 0.06}

# ---------------------------------------------------------------------------
# Drugs: key -> (ndc 11-digit, name, generic, specialty, therapeutic class, cost per 30 days, qty per 30 days)
# NDC labeler codes are synthetic (7xxxx) and do not correspond to real products.
# ---------------------------------------------------------------------------
DRUGS = {
    "metformin": ("70010012301", "Metformin HCl 500 mg tablet", "Y", "N", "Biguanide Antidiabetic", 8, 60),
    "glipizide": ("70010045601", "Glipizide 5 mg tablet", "Y", "N", "Sulfonylurea Antidiabetic", 10, 30),
    "insulin_glargine": ("70021078905", "Insulin glargine 100 unit/mL pen", "N", "N", "Insulin", 320, 15),
    "semaglutide": ("70021099101", "Semaglutide 1 mg/dose pen", "N", "N", "GLP-1 Receptor Agonist", 950, 3),
    "lisinopril": ("70033011201", "Lisinopril 10 mg tablet", "Y", "N", "ACE Inhibitor", 6, 30),
    "amlodipine": ("70033022401", "Amlodipine 5 mg tablet", "Y", "N", "Calcium Channel Blocker", 7, 30),
    "losartan": ("70033033601", "Losartan 50 mg tablet", "Y", "N", "Angiotensin II Receptor Blocker", 9, 30),
    "hctz": ("70033044801", "Hydrochlorothiazide 25 mg tablet", "Y", "N", "Thiazide Diuretic", 5, 30),
    "atorvastatin": ("70044010101", "Atorvastatin 20 mg tablet", "Y", "N", "Statin", 9, 30),
    "rosuvastatin": ("70044020201", "Rosuvastatin 10 mg tablet", "Y", "N", "Statin", 12, 30),
    "furosemide": ("70055010301", "Furosemide 40 mg tablet", "Y", "N", "Loop Diuretic", 6, 30),
    "carvedilol": ("70055020401", "Carvedilol 12.5 mg tablet", "Y", "N", "Beta Blocker", 8, 60),
    "sacubitril_valsartan": ("70055030501", "Sacubitril/valsartan 49/51 mg tablet", "N", "N", "ARNI", 650, 60),
    "apixaban": ("70055040601", "Apixaban 5 mg tablet", "N", "N", "Anticoagulant", 560, 60),
    "albuterol": ("70066010701", "Albuterol HFA 90 mcg inhaler", "Y", "N", "Short-Acting Beta Agonist", 35, 1),
    "fluticasone_salmeterol": ("70066020801", "Fluticasone/salmeterol 250/50 inhaler", "N", "N", "ICS/LABA Combination", 380, 1),
    "montelukast": ("70066030901", "Montelukast 10 mg tablet", "Y", "N", "Leukotriene Modifier", 12, 30),
    "levothyroxine": ("70077010101", "Levothyroxine 50 mcg tablet", "Y", "N", "Thyroid Hormone", 11, 30),
    "sertraline": ("70077020201", "Sertraline 50 mg tablet", "Y", "N", "SSRI Antidepressant", 9, 30),
    "escitalopram": ("70077030301", "Escitalopram 10 mg tablet", "Y", "N", "SSRI Antidepressant", 10, 30),
    "omeprazole": ("70077040401", "Omeprazole 20 mg capsule", "Y", "N", "Proton Pump Inhibitor", 9, 30),
    "adalimumab": ("70088010501", "Adalimumab 40 mg/0.4 mL pen", "N", "Y", "TNF Inhibitor", 6900, 2),
    "etanercept": ("70088020601", "Etanercept 50 mg/mL autoinjector", "N", "Y", "TNF Inhibitor", 6800, 4),
    "amoxicillin": ("70099010701", "Amoxicillin 500 mg capsule", "Y", "N", "Penicillin Antibiotic", 10, 30),
    "azithromycin": ("70099020801", "Azithromycin 250 mg tablet (Z-pak)", "Y", "N", "Macrolide Antibiotic", 14, 6),
    "cephalexin": ("70099030901", "Cephalexin 500 mg capsule", "Y", "N", "Cephalosporin Antibiotic", 12, 28),
    "ibuprofen": ("70099041001", "Ibuprofen 800 mg tablet", "Y", "N", "NSAID", 8, 30),
    "prednisone": ("70099051101", "Prednisone 20 mg tablet", "Y", "N", "Corticosteroid", 6, 10),
    "ondansetron": ("70099061201", "Ondansetron 4 mg ODT", "Y", "N", "Antiemetic", 12, 12),
    "oseltamivir": ("70099071301", "Oseltamivir 75 mg capsule", "Y", "N", "Neuraminidase Inhibitor", 45, 10),
}
ACUTE_DRUGS = ["amoxicillin", "azithromycin", "cephalexin", "ibuprofen", "prednisone", "ondansetron"]
PHARMACY_CHAINS = [("Golden State Pharmacy", 0.30), ("SaveMore Drug", 0.25), ("Desert Rx", 0.15),
                   ("Pacific Mail Order Pharmacy", 0.10), ("Independent", 0.20)]
