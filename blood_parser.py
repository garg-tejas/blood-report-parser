import re
import tempfile
import pytesseract
import pandas as pd
import streamlit as st
from pdf2image import convert_from_bytes
import io
from dotenv import load_dotenv

from medical_extraction import extract_parameters, add_standard_names, create_patterns, get_normal_ranges
from gemini_vision import configure_gemini, extract_with_gemini, answer_question_gemini

load_dotenv()

class BloodReportParser:
    def __init__(self, gemini_api_key=None, gemini_model_name="gemini-1.5-flash"):
        self.report_data = None
        self.test_data = None
        self.gemini_model = None
        self.gemini_model_name = gemini_model_name
        self.api_key = gemini_api_key
        
        self.standard_names = add_standard_names()
        self.patterns = create_patterns(self.standard_names)
        self.normal_ranges = get_normal_ranges()
        
        if gemini_api_key:
            self.gemini_model = configure_gemini(gemini_api_key, gemini_model_name)
        
    def extract_text_from_image(self, image):
        return pytesseract.image_to_string(image)
    
    def extract_text_from_pdf(self, pdf_file):
        try:
            pdf_bytes = pdf_file.read()
            
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            pages = len(reader.pages)
            
            if pages > 1:
                st.info(f"Processing {pages} page PDF. This may take a moment...")
                progress = st.progress(0)
            
            with tempfile.TemporaryDirectory() as path:
                images = convert_from_bytes(
                    pdf_bytes,
                    dpi=300,
                    output_folder=path,
                    thread_count=2,
                    fmt="jpeg"
                )
                
                text_parts = []
                for i, img in enumerate(images):
                    if pages > 1:
                        progress.progress((i+1)/pages)
                    
                    text = self.extract_text_from_image(img)
                    text_parts.append(f"--- PAGE {i+1} ---\n{text}")
                
                if pages > 1:
                    progress.progress(1.0)
                    
                return "\n\n".join(text_parts)
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"
    
    def parse_report(self, text):
        lines = text.split('\n')
        pattern = r'([A-Za-z\s]+)\s+([\d]+\.?[\d]*)\s+([A-Za-z/%]+)\s+\(?([\d\.-]+\s*-\s*[\d\.]+)?\)?'
        results = []
        
        for line in lines:
            match = re.search(pattern, line)
            if match:
                name = match.group(1).strip()
                try:
                    val_str = match.group(2)
                    if val_str and val_str != '.':
                        val = float(val_str)
                    else:
                        continue 
                        
                    units = match.group(3).strip()
                    ref_range = match.group(4) if match.group(4) else "N/A"
                    
                    status = "Normal"
                    if ref_range != "N/A":
                        try:
                            lower, upper = map(float, ref_range.split('-'))
                            if val < lower:
                                status = "Low"
                            elif val > upper:
                                status = "High"
                        except:
                            pass
                    
                    results.append({
                        "Test": name,
                        "Value": val,
                        "Units": units,
                        "Reference Range": ref_range,
                        "Status": status
                    })
                except ValueError:
                    continue
        
        self.test_data = pd.DataFrame(results)
        return self.test_data
    
    def advanced_parse_report(self, text):
        lines = text.split('\n')
        results = []
        
        for line in lines:
            match = re.search(r'([A-Za-z0-9\s\-\(\)]+?)\s+((?:\d+\.?\d*)|(?:\.\d+))\s*([A-Za-z0-9/%\s]+)(?:[\s\:]*([\d\.\-]+\s*-\s*[\d\.]+))?', line)
            
            if match:
                try:
                    parts = match.groups()
                    name = parts[0].strip()
                    
                    skip_terms = ['date', 'patient', 'doctor', 'page', 'reference', 'report']
                    if any(term in name.lower() for term in skip_terms) or len(name) < 2:
                        continue
                    
                    val_str = parts[1].strip()
                    val = float(val_str) if val_str else None
                    
                    if val is None:
                        continue
                    
                    units = parts[2].strip() if parts[2] else ""
                    ref_range = parts[3] if len(parts) > 3 and parts[3] else "N/A"
                    
                    status = "Normal"
                    if ref_range != "N/A":
                        try:
                            if '-' in ref_range:
                                lower, upper = map(float, ref_range.split('-'))
                                if val < lower:
                                    status = "Low"
                                elif val > upper:
                                    status = "High"
                        except:
                            pass
                    
                    results.append({
                        "Test": name,
                        "Value": val,
                        "Units": units,
                        "Reference Range": ref_range,
                        "Status": status
                    })
                except Exception:
                    continue
        
        if results:
            self.test_data = pd.DataFrame(results)
            return self.test_data
        else:
            return pd.DataFrame()
    
    def answer_question_basic(self, question):
        if self.test_data is None or len(self.test_data) == 0:
            return "Please upload a blood report first."
        
        question = question.lower()
        
        if "abnormal" in question or "concerning" in question:
            abnormal = self.test_data[self.test_data["Status"] != "Normal"]
            if len(abnormal) == 0:
                return "All test results are within normal ranges."
            
            response = "The following test results are outside normal ranges:\n"
            for _, row in abnormal.iterrows():
                response += f"- {row['Test']}: {row['Value']} {row['Units']} (Reference: {row['Reference Range']})\n"
            return response
        
        for _, row in self.test_data.iterrows():
            test_name = row["Test"].lower()
            if test_name in question:
                return f"{row['Test']}: {row['Value']} {row['Units']} (Reference Range: {row['Reference Range']}, Status: {row['Status']})"
        
        if "highest" in question:
            highest = self.test_data.loc[self.test_data["Value"].idxmax()]
            return f"The highest value is for {highest['Test']}: {highest['Value']} {highest['Units']}"
        
        if "lowest" in question:
            lowest = self.test_data.loc[self.test_data["Value"].idxmin()]
            return f"The lowest value is for {lowest['Test']}: {lowest['Value']} {lowest['Units']}"
        
        return "I couldn't understand your question. Please try to ask about specific tests or abnormal values."
    
    def answer_question(self, question, use_gemini=True):
        if use_gemini and self.gemini_model is not None:
            source, answer = answer_question_gemini(self.gemini_model, question, self.test_data, self.gemini_model_name)
            if answer is None:
                return source, self.answer_question_basic(question)
            return source, answer
        else:
            return "Basic Response:", self.answer_question_basic(question)
    
    def answer_question_from_data(self, question, use_gemini=True):
        if self.test_data is None or self.test_data.empty:
            return "Error:", "No blood test data available to answer questions."
            
        if use_gemini and self.gemini_model is not None:
            source, answer = answer_question_gemini(
                self.gemini_model, 
                question, 
                self.test_data, 
                self.gemini_model_name
            )
            if answer is None:
                return "Basic Response:", self.answer_question_basic(question)
            return source, answer
        else:
            return "Basic Response:", self.answer_question_basic(question)
            
    def set_gemini_model(self, model_name):
        if not self.api_key:
            return False
            
        try:
            self.gemini_model_name = model_name
            self.gemini_model = configure_gemini(self.api_key, model_name)
            return True
        except Exception as e:
            st.error(f"Error setting model: {str(e)}")
            return False

    def extract_data_with_gemini(self, file_bytes, file_type):
        result, msg = extract_with_gemini(self.gemini_model, file_bytes, file_type)
        if result is not None and not result.empty:
            self.test_data = result
        return result, msg
            
    def extract_specialized_parameters(self, ocr_text):
        return extract_parameters(ocr_text, self.standard_names, self.patterns, self.normal_ranges)