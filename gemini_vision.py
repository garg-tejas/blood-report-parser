import base64
import re
import pandas as pd
import google.generativeai as genai

def configure_gemini(api_key, model_name="gemini-1.5-flash"):
    if not api_key:
        return None
        
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error configuring Gemini model: {str(e)}")
        return None

def extract_with_gemini(model, file_bytes, file_type):
    if model is None:
        return None, "Gemini API not configured."
    
    try:
        encoded_file = base64.b64encode(file_bytes).decode('utf-8')
        
        prompt = """
        You are a specialized medical data extraction AI analyzing a blood report. Extract ALL legitimate medical test parameters, not just common ones.

        IMPORTANT:
        - Blood reports may contain standard tests AND specialized/less common tests that are still medically valid
        - Look for all test parameters with numeric values, even if they're not in the common lists
        - Extract ANY term that appears to be a medical test measurement

        EXTRACT the following in this format:
        TEST_NAME: VALUE UNITS (REFERENCE_RANGE)

        DO NOT INCLUDE:
        - Administrative data (patient info, doctor names, dates, lab info)
        - Non-test information like addresses, phone numbers, page numbers

        EXAMPLES OF TESTS TO EXTRACT (not limited to these):
        1. ALL common blood parameters: Hemoglobin, RBC, WBC, Platelets, etc.
        2. ALL biochemistry markers: Glucose, Electrolytes, Liver enzymes, etc.
        3. ALL specialized tests: Tumor markers, Hormones, Vitamins, Immunology markers
        4. ANY parameter with numeric values and medical significance
        5. ANY specialized tests with medical terminology, even if uncommon

        YOUR GOAL: Be comprehensive and extract EVERY medical test parameter present, even ones not listed in common blood test categories.

        FORMAT YOUR RESPONSE AS A CLEAN LIST OF VALID TESTS ONLY.
        """
        
        image_part = {
            "mime_type": file_type,
            "data": encoded_file
        }
        
        response = model.generate_content([prompt, image_part])
        extracted_text = response.text
        
        tests = []
        for line in extracted_text.split('\n'):
            line = line.strip()
            if not line or ':' not in line:
                continue
                
            try:
                parts = line.split(':')
                if len(parts) < 2:
                    continue
                    
                name = parts[0].strip().replace('*', '').replace('_', ' ').strip()
                val_part = parts[1].strip()
                
                skip_terms = ['date', 'patient', 'doctor', 'name', 'id', 'address', 'phone', 'fax']
                if any(term in name.lower() for term in skip_terms) or len(name) < 2:
                    continue
                
                val_match = re.search(r'([\d\.]+)', val_part)
                if not val_match:
                    continue
                    
                val = float(val_match.group(1))
                
                units_match = re.search(r'[\d\.]+\s+([A-Za-z/%0-9\s]+)', val_part)
                units = units_match.group(1).strip() if units_match else ""
                
                ref_range = "N/A"
                ref_match = re.search(r'\(([^)]+)\)', val_part)
                if ref_match:
                    ref_range = ref_match.group(1)
                
                status = "Normal"
                if ref_range != "N/A" and '-' in ref_range:
                    try:
                        lower, upper = map(float, ref_range.split('-'))
                        if val < lower:
                            status = "Low"
                        elif val > upper:
                            status = "High"
                    except:
                        pass
                
                # Validate plausibility
                valid = True
                ranges = {
                    "hemoglobin": (1, 25),
                    "wbc": (0.1, 100),
                    "rbc": (0.5, 10),
                    "platelets": (1, 1000),
                    "glucose": (10, 600),
                    "cholesterol": (50, 600),
                    "sodium": (100, 180),
                    "potassium": (1, 10),
                }
                
                for keyword, (min_val, max_val) in ranges.items():
                    if keyword in name.lower() and (val < min_val or val > max_val):
                        valid = False
                        break
                
                if valid:
                    tests.append({
                        "Test": name,
                        "Value": val,
                        "Units": units,
                        "Reference Range": ref_range,
                        "Status": status
                    })
            except Exception:
                continue
                
        if tests:
            return pd.DataFrame(tests), "Success"
        else:
            return None, "No test data could be extracted by Gemini model."
            
    except Exception as e:
        return None, f"Error with Gemini extraction: {str(e)}"

def answer_question_gemini(model, question, test_data, model_name):
    if model is None or test_data is None or len(test_data) == 0:
        return "Error:", "No data available or Gemini API is not configured."
    
    try:
        normal = test_data[test_data["Status"] == "Normal"]
        abnormal = test_data[test_data["Status"] != "Normal"]
        
        context = "Blood Test Results:\n\n"
        
        if not abnormal.empty:
            context += "ABNORMAL RESULTS:\n"
            for _, row in abnormal.iterrows():
                direction = "ELEVATED" if row['Status'] == "High" else "LOW" 
                context += f"- {row['Test']}: {row['Value']} {row['Units']} ({direction}, Reference Range: {row['Reference Range']})\n"
            context += "\n"
            
        if not normal.empty:
            context += "NORMAL RESULTS:\n"
            for _, row in normal.iterrows():
                context += f"- {row['Test']}: {row['Value']} {row['Units']} (Reference Range: {row['Reference Range']})\n"
        
        prompt = f"""
        You are a medical assistant helping interpret blood test results. Answer the following question based ONLY on the blood test data provided.
        
        {context}
        
        QUESTION: {question}
        
        IMPORTANT GUIDELINES:
        1. Only discuss tests that appear in the results above
        2. For abnormal values, explain what they might indicate without making definitive diagnoses
        3. If asked about a test that isn't in the data, clearly state that information is not available
        4. Use simple, patient-friendly language
        5. Include relevant reference ranges when discussing specific tests
        6. Always recommend consulting a healthcare professional for medical advice
        
        YOUR ANSWER:
        """
        
        response = model.generate_content(prompt)
        return f"Gemini Medical Assistant:", response.text
    except Exception as e:
        return f"Error using Gemini API: {str(e)}", None