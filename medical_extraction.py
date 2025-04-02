import re
import pandas as pd

def clean_ocr_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'g/dL', 'g/dL', text, flags=re.IGNORECASE) 
    text = re.sub(r'mmol/L', 'mmol/L', text, flags=re.IGNORECASE)
    return text

def add_standard_names():
    return {
        # CBC parameters
        "WBC": ["white blood cell", "leukocyte", "white cell", "white blood cell count", "leukocyte count"],
        "RBC": ["red blood cell", "erythrocyte", "red cell", "red blood cell count", "erythrocyte count"],
        "HGB": ["hemoglobin", "haemoglobin", "hgb", "hb", "hemoglobin concentration"],
        "HCT": ["hematocrit", "haematocrit", "packed cell volume", "pcv", "hct", "crit"],
        "MCV": ["mean corpuscular volume", "mean cell volume", "mean erythrocyte volume"],
        "MCH": ["mean corpuscular hemoglobin", "mean cell hemoglobin", "mean erythrocyte hemoglobin"],
        "MCHC": ["mean corpuscular hemoglobin concentration", "mean cell hemoglobin concentration"],
        "PLT": ["platelet", "thrombocyte", "platelet count", "thrombocyte count"],
        "RDW": ["red cell distribution width", "rdw-cv", "rdw-sd", "red blood cell distribution width"],
        "MPV": ["mean platelet volume", "average platelet volume"],
        
        # WBC Differential
        "NEUT": ["neutrophil", "neutrophils", "neutrophil count", "segmented neutrophils", "segs", "polys"],
        "LYMPH": ["lymphocyte", "lymphocytes", "lymphocyte count", "lymphs"],
        "MONO": ["monocyte", "monocytes", "monocyte count", "monos"],
        "EOS": ["eosinophil", "eosinophils", "eosinophil count", "eos"],
        "BASO": ["basophil", "basophils", "basophil count", "basos"],
        "BAND": ["band neutrophil", "band cells", "band forms", "bands", "stab cells"],
        
        # Chemistry panel
        "GLUC": ["glucose", "blood sugar", "fasting glucose", "blood glucose", "plasma glucose", "sugar"],
        "BUN": ["blood urea nitrogen", "urea nitrogen", "urea", "bun-creatinine ratio"],
        "CREA": ["creatinine", "creat", "serum creatinine"],
        "ALT": ["alanine aminotransferase", "alanine transaminase", "sgpt", "alat"],
        "AST": ["aspartate aminotransferase", "aspartate transaminase", "sgot", "asat"],
        "ALP": ["alkaline phosphatase", "alp", "alkphos"],
        "TBIL": ["total bilirubin", "bilirubin total", "total serum bilirubin"],
        "DBIL": ["direct bilirubin", "conjugated bilirubin", "bilirubin direct"],
        "IBIL": ["indirect bilirubin", "unconjugated bilirubin", "bilirubin indirect"],
        "ALB": ["albumin", "serum albumin", "alb"],
        "TP": ["total protein", "protein total", "total serum protein"],
        "GLOB": ["globulin", "globulins", "serum globulins"],
        "GGT": ["gamma-glutamyl transferase", "gamma-glutamyl transpeptidase", "ggt", "gamma gt"],
        "LDH": ["lactate dehydrogenase", "lactic dehydrogenase", "ldh"],
        
        # Lipid panel
        "CHOL": ["cholesterol", "total cholesterol", "serum cholesterol", "tc"],
        "HDL": ["hdl cholesterol", "high-density lipoprotein", "hdl-c", "good cholesterol"],
        "LDL": ["ldl cholesterol", "low-density lipoprotein", "ldl-c", "bad cholesterol"],
        "TRIG": ["triglycerides", "tg", "trigs"],
        "VLDL": ["very low-density lipoprotein", "vldl-c", "vldl cholesterol"],
        "NON-HDL": ["non-hdl cholesterol", "non hdl", "non-hdl-c"],
        "CHOL/HDL": ["cholesterol/hdl ratio", "tc/hdl ratio", "cardiac risk ratio"],
        
        # Electrolytes
        "NA": ["sodium", "na+", "serum sodium"],
        "K": ["potassium", "k+", "serum potassium"],
        "CL": ["chloride", "cl-", "serum chloride"],
        "CA": ["calcium", "ca++", "serum calcium", "total calcium"],
        "ION-CA": ["ionized calcium", "free calcium"],
        "MG": ["magnesium", "mg++", "serum magnesium"],
        "PHOS": ["phosphorus", "phosphate", "serum phosphorus", "phosphorous"],
        "BICARB": ["bicarbonate", "hco3", "carbon dioxide", "co2", "total co2"],
        
        # Kidney function
        "EGFR": ["estimated glomerular filtration rate", "gfr", "estimated gfr", "egfr"],
        "UACR": ["urine albumin-to-creatinine ratio", "albumin/creatinine ratio", "microalbumin/creatinine ratio"],
        "CYSTATIN-C": ["cystatin c", "cystatin"],
        
        # Diabetes markers
        "A1C": ["hemoglobin a1c", "glycated hemoglobin", "hba1c", "a1c", "glycohemoglobin", "glycosylated hemoglobin"],
        "FBS": ["fasting blood sugar", "fasting glucose", "fpg", "fasting plasma glucose"],
        "INSULIN": ["insulin level", "fasting insulin", "serum insulin"],
        "C-PEPTIDE": ["c-peptide", "connecting peptide"],
        "HOMA-IR": ["homeostatic model assessment of insulin resistance", "insulin resistance index"],
        
        # Thyroid panel
        "TSH": ["thyroid stimulating hormone", "thyrotropin", "thyroid-stimulating hormone", "thyroid function"],
        "FT4": ["free t4", "free thyroxine", "ft4", "free tetraiodothyronine"],
        "T4": ["thyroxine", "total t4", "tetraiodothyronine", "total thyroxine"],
        "FT3": ["free t3", "free triiodothyronine", "ft3"],
        "T3": ["triiodothyronine", "total t3", "t3", "total triiodothyronine"],
        "RT3": ["reverse t3", "reverse triiodothyronine"],
        "ANTI-TPO": ["anti-thyroid peroxidase antibodies", "tpo antibodies", "thyroid peroxidase antibodies"],
        "ANTI-TG": ["anti-thyroglobulin antibodies", "tg antibodies", "thyroglobulin antibodies"],
        
        # Iron studies
        "IRON": ["serum iron", "iron", "fe"],
        "FERR": ["ferritin", "serum ferritin"],
        "TIBC": ["total iron binding capacity", "tibc"],
        "TSAT": ["transferrin saturation", "iron saturation", "percent saturation", "transferrin saturation percentage"],
        "TRANSFERRIN": ["transferrin", "serum transferrin"],
        
        # Coagulation tests
        "INR": ["international normalized ratio", "prothrombin time international normalized ratio"],
        "PT": ["prothrombin time", "pro time"],
        "APTT": ["activated partial thromboplastin time", "aptt", "ptt", "partial thromboplastin time"],
        "FIBRINOGEN": ["fibrinogen", "factor i", "plasma fibrinogen"],
        "D-DIMER": ["d-dimer", "fibrin degradation fragment", "fibrin split products"],
        
        # Inflammatory markers
        "CRP": ["c-reactive protein", "crp test", "high-sensitivity crp", "hs-crp"],
        "ESR": ["erythrocyte sedimentation rate", "sed rate", "esr test", "sedimentation rate"],
        "IL-6": ["interleukin 6", "interleukin-6", "il6"],
        "TNF": ["tumor necrosis factor", "tnf-alpha", "tnf alpha"],
        
        # Vitamins and minerals
        "VIT_D": ["vitamin d", "25-oh vitamin d", "25-hydroxyvitamin d", "25-oh d", "calcidiol"],
        "VIT_B12": ["vitamin b12", "cobalamin", "cyanocobalamin"],
        "FOLATE": ["folate", "folic acid", "vitamin b9"],
        "ZINC": ["zinc", "zn", "serum zinc"],
        "COPPER": ["copper", "cu", "serum copper"],
        "SELENIUM": ["selenium", "se", "serum selenium"],
        
        # Liver function additional
        "AMMONIA": ["ammonia", "blood ammonia", "nh3"],
        "ALPHAFETOPROTEIN": ["alpha-fetoprotein", "afp", "alpha fetoprotein"],
        
        # Cardiac markers
        "TROPONIN": ["troponin", "troponin i", "troponin t", "cardiac troponin", "ctn", "ctni", "ctnt"],
        "CK-MB": ["creatine kinase-mb", "ck-mb", "creatine kinase myocardial band"],
        "BNP": ["brain natriuretic peptide", "b-type natriuretic peptide", "bnp"],
        "NT-PROBNP": ["n-terminal pro b-type natriuretic peptide", "nt-probnp", "pro-bnp"],
        "MYOGLOBIN": ["myoglobin", "serum myoglobin"],
        
        # Hormones
        "TESTOSTERONE": ["testosterone", "total testosterone", "serum testosterone"],
        "FREE-TEST": ["free testosterone", "bioavailable testosterone"],
        "ESTRADIOL": ["estradiol", "e2", "oestradiol"],
        "PROGESTERONE": ["progesterone", "p4"],
        "CORTISOL": ["cortisol", "serum cortisol", "hydrocortisone level"],
        "DHEA-S": ["dehydroepiandrosterone sulfate", "dhea-sulfate", "dheas"],
        "PROLACTIN": ["prolactin", "prl", "lactogenic hormone"],
        "FSH": ["follicle stimulating hormone", "follicle-stimulating hormone"],
        "LH": ["luteinizing hormone", "luteinising hormone"],
        
        # Immunology
        "ANA": ["antinuclear antibody", "antinuclear antibodies", "ana test"],
        "RF": ["rheumatoid factor", "rheumatoid arthritis factor"],
        "ANTI-CCP": ["anti-cyclic citrullinated peptide", "anti-ccp antibodies", "anti-citrullinated protein antibodies"],
        "C3": ["complement component 3", "complement c3"],
        "C4": ["complement component 4", "complement c4"],
        "IGA": ["immunoglobulin a", "iga test"],
        "IGG": ["immunoglobulin g", "igg test"],
        "IGM": ["immunoglobulin m", "igm test"],
        "IGE": ["immunoglobulin e", "ige test"],
        
        # Tumor markers
        "PSA": ["prostate specific antigen", "prostate-specific antigen", "total psa"],
        "FREE-PSA": ["free prostate specific antigen", "free psa", "percent free psa"],
        "CEA": ["carcinoembryonic antigen", "carcinoembryonic antigen test"],
        "CA-125": ["cancer antigen 125", "ca 125", "carcinoma antigen 125"],
        "CA-19-9": ["cancer antigen 19-9", "ca 19-9", "carbohydrate antigen 19-9"],
        "CA-15-3": ["cancer antigen 15-3", "ca 15-3", "carcinoma antigen 15-3"],
        
        # Arterial blood gases
        "PH": ["ph", "blood ph", "arterial ph"],
        "PCO2": ["partial pressure of carbon dioxide", "pco2", "carbon dioxide pressure"],
        "PO2": ["partial pressure of oxygen", "po2", "oxygen pressure"],
        "HCO3": ["bicarbonate", "serum bicarbonate"],
        "BE": ["base excess", "base deficit"],
        "LACTIC-ACID": ["lactic acid", "lactate", "blood lactate"]
    }

def create_patterns(standard_names):
    patterns = {}
    for test_id, synonyms in standard_names.items():
        synonym_pattern = "|".join([re.escape(syn.lower()) for syn in synonyms])
        
        primary_pattern = rf"(?P<test>{synonym_pattern})[:\s]*(?P<value>\d+\.?\d*)\s*(?P<units>\w+(?:/\w+)?)?(?:\s*\(?(?P<range>\d+\.?\d*\s*-\s*\d+\.?\d*)\)?)?"
        
        secondary_pattern = rf"(?P<test>{synonym_pattern})[:\s]*(?P<value>\d+\.?\d*)"
        
        patterns[test_id] = [primary_pattern, secondary_pattern]
    
    return patterns

def get_normal_ranges():
    return {
        "WBC": ("4.5", "11.0", "10^3/µL"),
        "RBC": ("4.5", "5.9", "10^6/µL"),
        "HGB": ("13.5", "17.5", "g/dL"),
        "HCT": ("41.0", "50.0", "%"),
        "MCV": ("80.0", "100.0", "fL"),
        "MCH": ("27.0", "33.0", "pg"),
        "MCHC": ("32.0", "36.0", "g/dL"),
        "PLT": ("150", "450", "10^3/µL"),
        
        "GLUC": ("70", "99", "mg/dL"),
        "BUN": ("7", "20", "mg/dL"),
        "CREA": ("0.6", "1.2", "mg/dL"),
        "ALT": ("7", "56", "U/L"),
        "AST": ("10", "40", "U/L"),
        "ALP": ("44", "147", "U/L"),
        "TBIL": ("0.1", "1.2", "mg/dL"),
        "ALB": ("3.4", "5.4", "g/dL"),
        "TP": ("6.0", "8.3", "g/dL"),
        
        "CHOL": ("0", "200", "mg/dL"),
        "HDL": ("40", "60", "mg/dL"),
        "LDL": ("0", "100", "mg/dL"),
        "TRIG": ("0", "150", "mg/dL"),
        
        "NA": ("135", "145", "mmol/L"),
        "K": ("3.5", "5.0", "mmol/L"),
        "CL": ("98", "107", "mmol/L"),
        "CA": ("8.5", "10.5", "mg/dL"),
        "MG": ("1.7", "2.2", "mg/dL"),
        "PHOS": ("2.5", "4.5", "mg/dL"),
        
        "A1C": ("4.0", "5.6", "%"),
        "TSH": ("0.5", "5.0", "mIU/L"),
        "T4": ("0.8", "1.8", "ng/dL"),
        "T3": ("2.3", "4.2", "pg/mL"),
        "FER": ("30", "400", "ng/mL"),
        "VIT_D": ("30", "100", "ng/mL"),
        "VIT_B12": ("200", "900", "pg/mL"),
        "FOL": ("2.7", "17.0", "ng/mL"),
        "CRP": ("0", "8", "mg/L"),
        "ESR": ("0", "15", "mm/hr"),
        "INR": ("0.8", "1.2", "")
    }

def extract_parameters(ocr_text, standard_names, patterns, normal_ranges):
    clean_text = clean_ocr_text(ocr_text)
    results = []
    
    for test_id, pattern_list in patterns.items():
        for pattern in pattern_list:
            for match in re.finditer(pattern, clean_text.lower()):
                try:
                    match_dict = match.groupdict()
                    
                    test_name = match_dict.get('test', '').strip()
                    if test_name:
                        test_name = standard_names[test_id][0].title()
                    
                    value = match_dict.get('value', '')
                    if value:
                        try:
                            value = float(value)
                        except ValueError:
                            continue
                    else:
                        continue
                    
                    units = match_dict.get('units', '') or normal_ranges[test_id][2]
                    range_val = match_dict.get('range', '')
                    
                    if not range_val:
                        range_val = f"{normal_ranges[test_id][0]}-{normal_ranges[test_id][1]}"
                    
                    status = "Normal"
                    try:
                        low, high = map(float, range_val.split('-'))
                        if value < low:
                            status = "Low"
                        elif value > high:
                            status = "High"
                    except:
                        pass
                    
                    results.append({
                        "Test": test_name,
                        "Value": value,
                        "Units": units,
                        "Reference Range": range_val,
                        "Status": status
                    })
                except Exception as e:
                    continue
    
    if results:
        df = pd.DataFrame(results)
        df = df.drop_duplicates(subset=['Test'], keep='first')
        return df
    else:
        return pd.DataFrame()