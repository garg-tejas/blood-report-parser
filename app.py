import os
import streamlit as st
from PIL import Image
import pandas as pd
import io
import urllib.parse
import hashlib
from datetime import datetime
import uuid
import httpx
from blood_parser import BloodReportParser
from database import BloodReportDatabase
from auth import Auth0Management, get_auth_status, set_auth_cookie, clear_auth, require_auth
from dotenv import load_dotenv

if not os.getenv("STREAMLIT_SERVER_MODE"):  
    load_dotenv()

def get_unique_key(base_name='widget'):
    """Generate a unique key for Streamlit widgets to prevent duplicate key errors"""
    return f"{base_name}_{uuid.uuid4().hex[:8]}"

@st.cache_data
def cached_extract_with_gemini(file_bytes, file_type, api_key, model_name):
    from blood_parser import BloodReportParser
    parser = BloodReportParser(gemini_api_key=api_key, gemini_model_name=model_name)
    return parser.extract_data_with_gemini(file_bytes, file_type)

def filter_false_positives(df):
    if df is None or df.empty:
        return df
    
    skip_words = [
        'page', 'street', 'address', 'phone', 'fax', 'email', 
        'date', 'time', 'report', 'sample', 'lab', 
        'hospital', 'doctor', 'patient', 'reference', 'iso', 
        'area', 'city', 'state', 'action', 'order',
        'variation', 'screening'
    ]
    
    mask = ~df['Test'].str.lower().str.contains('|'.join(skip_words), regex=True)
    mask &= ~df['Test'].str.match(r'^\d+$')
    mask &= ~df['Test'].str.lower().str.contains(r'page|of|street|area|iso')
    mask &= df['Test'].str.len() > 2
    
    valid_terms = [
        'haem', 'hemo', 'wbc', 'rbc', 'platelet', 'lymph', 'mono', 'neutro', 'baso',
        'eosin', 'hct', 'mcv', 'mch', 'mchc', 'rdw', 'mpv', 'count', 'cell', 'band',
        'glucose', 'hba1c', 'chol', 'trigly', 'hdl', 'ldl', 'vldl', 'creat',
        'urea', 'uric', 'bili', 'protein', 'albumin', 'glob', 'ast', 'alt', 'alp',
        'ggt', 'ldh', 'amylase', 'lipase',
        'sodium', 'potassium', 'chloride', 'calcium', 'phosph', 'magnes', 'bicarb',
        'iron', 'ferritin', 'vitamin', 'folate', 'b12', 'tsh', 't3', 't4', 'ft3', 'ft4', 
        'cortisol', 'estrogen', 'testosterone', 'progesterone', 'insulin', 'prolactin',
        'psa', 'cea', 'afp', 'ca', 'beta', 'hcg',
        'esr', 'crp', 'rf', 'ana',
        'blood', 'serum', 'plasma', 'acid', 'phosphatase', 'transferase',
        'electro', 'lipid', 'liver', 'kidney', 'thyroid', 'hormone', 'enzym',
        'ratio', 'index', 'total', 'direct', 'indirect', 'free', 'bound', 'clearance',
        'fraction', 'level', 'concentration', 'mass', 'volume',
        'troponin', 'bnp', 'fibrinogen', 'd-dimer', 'inr', 'aptt', 'pt',
        'homocysteine', 'cystatin', 'egfr', 'iga', 'igg', 'igm', 'ige'
    ]
    
    valid_tests = df['Test'].str.lower().str.contains('|'.join(valid_terms), regex=True)
    med_number = r'(?:cd\d+)|(?:t\d+)|(?:b\d+)|(?:d\d+)|(?:vitamin\s+[a-e]\d*)|(?:coenzyme\s+q\d+)'
    valid_numbered = df['Test'].str.lower().str.contains(med_number, regex=True)
    
    final_mask = mask | valid_tests | valid_numbered
    
    return df[final_mask].reset_index(drop=True)

def answer_question_with_data(parser, question, use_gemini):
    if parser.test_data is None or parser.test_data.empty:
        return "Error:", "No blood test data available to answer questions."
        
    if use_gemini and parser.gemini_model is not None:
        from gemini_vision import answer_question_gemini
        source, answer = answer_question_gemini(
            parser.gemini_model, 
            question, 
            parser.test_data, 
            parser.gemini_model_name
        )
        if answer is None:
            return "Basic Response:", parser.answer_question_basic(question)
        return source, answer
    else:
        return "Basic Response:", parser.answer_question_basic(question)

def switch_to_qa_mode():
    st.session_state.app_mode = "qa"
    
def switch_to_display_mode():
    st.session_state.app_mode = "display"

def switch_to_history_mode():
    st.session_state.app_mode = "history"

def check_auth0_connection():
    """Diagnostic function to check Auth0 connectivity"""
    st.title("Auth0 Configuration Check")
    
    auth0_domain = st.text_input("Auth0 Domain:", 
                                value=os.getenv("AUTH0_DOMAIN", ""),
                                placeholder="e.g., dev-example.us.auth0.com",
                                key=get_unique_key("domain_input"))
    
    callback_url = st.text_input("Callback URL:", 
                                value=os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8501/"),
                                placeholder="e.g., http://localhost:8501/",
                                key=get_unique_key("callback_input"))
    
    if st.button("Test Connection", key=get_unique_key("test_conn")):
        if not auth0_domain:
            st.error("Please enter your Auth0 domain")
            return
            
        if auth0_domain.startswith(('http://', 'https://')):
            st.warning("Auth0 domain should not include protocol (http:// or https://)")
            auth0_domain = auth0_domain.split('//')[1]
            
        st.info(f"Testing connection to: https://{auth0_domain}/.well-known/openid-configuration")
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"https://{auth0_domain}/.well-known/openid-configuration")
                
                if response.status_code == 200:
                    st.success("✅ Connection successful! Auth0 domain is valid.")
                    metadata = response.json()
                    st.json(metadata)
                else:
                    st.error(f"❌ Connection failed with status code: {response.status_code}")
                    st.error(f"Response: {response.text}")
        except Exception as e:
            st.error(f"❌ Connection error: {str(e)}")
            st.markdown("""
            ### Common reasons for connection failures:
            
            1. **Domain is incorrect**: Verify the domain in your Auth0 dashboard 
            2. **Network issues**: Check if your network is blocking the connection
            3. **Auth0 service status**: Check if Auth0 is experiencing issues
            
            Try opening the URL directly in your browser to see if it's accessible.
            """)
    
    st.divider()
    
    st.markdown("""
    ### How to correctly set up Auth0:
    
    1. **Auth0 Application Settings**:
        - Application type should be "Regular Web Application"
        - Ensure "Token Endpoint Authentication Method" is set to "POST"
        - Enable CORS (Allow Cross-Origin Authentication)
    
    2. **Allowed URLs in Auth0 Dashboard**:
        - Allowed Callback URLs: `{callback_url}`
        - Allowed Web Origins: `{app_origin}`
        - Allowed Logout URLs: `{callback_url}`
        
        The callback URL must **exactly** match what's in your environment variables, including trailing slashes.
    
    3. **Environment Variables**:
        - AUTH0_DOMAIN={auth0_domain}
        - AUTH0_CLIENT_ID=(from Auth0 dashboard)
        - AUTH0_CLIENT_SECRET=(from Auth0 dashboard)
        - AUTH0_CALLBACK_URL={callback_url}
    """.format(
        callback_url=callback_url,
        app_origin="/".join(callback_url.split("/")[:3]),
        auth0_domain=auth0_domain
    ))
    
    st.markdown("""
    ### Common Auth0 Errors:
    
    - **"Refused to connect"**: Usually means the domain is incorrect or there's a network issue
    - **"invalid redirect_uri"**: Your callback URL doesn't match what's in Auth0 dashboard
    - **"unauthorized_client"**: Client ID/Secret is incorrect or application type is wrong
    """)

def handle_auth_callback():
    """Handle OAuth callback from Auth0"""    
    query_params = st.query_params

    if "code" in query_params:
        code = query_params.get("code")
                
        auth = Auth0Management()
        user_info = auth.handle_callback(code)
        
        if user_info:
            set_auth_cookie(user_info)
            st.success("Login successful!")
            
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Authentication failed. Please try again or try using a different browser.")
            with st.expander("Troubleshooting Tips"):
                st.markdown("""
                **Common issues:**
                - Cookies might be blocked in private browsing
                - Third-party cookies might be disabled in your browser
                - You may need to clear your browser cache
                - Try using a different browser
                
                If problems persist, please contact support.
                """)

def render_auth_ui():
    """Render authentication UI"""
    auth = Auth0Management()
    is_authenticated = get_auth_status()
    
    if is_authenticated:
        user = st.session_state.auth_user
        user_name = user.get('name', user.get('email', 'User'))
        
        with st.sidebar.container():
            st.write(f"👤 Logged in as: **{user_name}**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Your Reports", key=get_unique_key("your_reports")):
                    switch_to_history_mode()
                    st.rerun()
            with col2:
                if st.button("Logout", key=get_unique_key("logout")):
                    clear_auth()
                    st.rerun()
    else:
        with st.sidebar.container():
            st.write("👤 Not logged in")
            
            if auth.config_valid:
                login_url = auth.get_login_url()
                st.markdown(f'''
                <a href="{login_url}" target="_self">
                    <button style="
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 15px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 16px;
                        width: 100%;
                    ">
                        Login with Auth0
                    </button>
                </a>
                ''', unsafe_allow_html=True)
                
                st.markdown("""
                <small>Login to save your reports and access your history.</small>
                """, unsafe_allow_html=True)
            else:
                st.error("Auth0 is not properly configured.")

def save_current_report(db, user_id, report_data, file_name=None):
    """Save the current report to the database"""
    if not file_name:
        file_name = "Unnamed Report"
        
    report_date = st.date_input("Report Date", datetime.now(), key=get_unique_key("report_date"))
    
    if st.button("Save Report", key=get_unique_key("save_report")):
        with st.spinner("Saving report..."):
            report_id = db.save_report(user_id, report_data, file_name, report_date)
            
            if report_id:
                st.success(f"Report saved successfully! (ID: {report_id})")
                return True
            else:
                st.error("Failed to save report.")
                return False
    
    return False

def render_history_page(db):
    """Render the user's report history page"""
    require_auth()
    user_id = st.session_state.auth_user.get('sub')
    
    st.title("Your Blood Report History")
    
    if st.button("← Back to Home", key=get_unique_key("back_to_home")):
        switch_to_display_mode()
        st.rerun()
    
    reports = db.get_user_reports(user_id)
    
    if not reports:
        st.info("You don't have any saved reports yet.")
        return
    
    st.write(f"You have {len(reports)} saved reports.")
    
    if 'selected_report_id' in st.session_state:
        selected_report = db.get_report_by_id(st.session_state.selected_report_id)
        
        if selected_report and "data_df" in selected_report:
            st.success(f"Viewing Report: {selected_report.get('file_name', 'Unnamed Report')}")
            report_date = selected_report.get('report_date')
            if report_date:
                st.write(f"Report Date: {report_date.strftime('%Y-%m-%d')}")
            if st.button("← Back to Report List", key=get_unique_key("back_to_report_list")):
                del st.session_state.selected_report_id
                st.rerun()
            st.subheader("Blood Test Results")
            def highlight_status(row):
                colors = pd.Series([''] * len(row), index=row.index)
                if 'Status' in row and row['Status'] == 'High':
                    colors = pd.Series(['background-color: rgba(220, 53, 69, 0.8); color: white'] * len(row), index=row.index)
                elif 'Status' in row and row['Status'] == 'Low':
                    colors = pd.Series(['background-color: rgba(255, 193, 7, 0.8); color: black'] * len(row), index=row.index)
                return colors
            
            test_data = selected_report["data_df"]
            st.dataframe(test_data.style.apply(highlight_status, axis=1))
            st.subheader("EHR Style Visualization")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Normal Results")
                normal = test_data[test_data["Status"] == "Normal"]
                if len(normal) > 0:
                    for _, row in normal.iterrows():
                        st.markdown(f"✅ **{row['Test']}**: {row['Value']} {row['Units']}")
                else:
                    st.write("No normal results found.")
            
            with col2:
                st.markdown("#### Abnormal Results")
                abnormal = test_data[test_data["Status"] != "Normal"]
                if len(abnormal) > 0:
                    for _, row in abnormal.iterrows():
                        if row['Status'] == "High":
                            st.markdown(f"""
                            <div style="padding: 10px; border-radius: 5px; margin-bottom: 10px; 
                            background-color: rgba(220, 53, 69, 0.2); border-left: 4px solid #dc3545;">
                            <span style="color: #dc3545; font-weight: bold;">↑ {row['Test']}</span>: {row['Value']} {row['Units']} 
                            <br/><small>Reference range: {row['Reference Range']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="padding: 10px; border-radius: 5px; margin-bottom: 10px; 
                            background-color: rgba(255, 193, 7, 0.2); border-left: 4px solid #ffc107;">
                            <span style="color: #ffc107; font-weight: bold;">↓ {row['Test']}</span>: {row['Value']} {row['Units']} 
                            <br/><small>Reference range: {row['Reference Range']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.write("No abnormal results found.")
            st.markdown("---")
            st.subheader("Ask Questions About This Report")
            
            from blood_parser import BloodReportParser
            parser = BloodReportParser()
            parser.test_data = test_data
            
            question = st.text_input("Enter your question:", key=get_unique_key("history_question_input"))
            use_gemini = st.checkbox("Use Gemini for Q&A (requires API key)", value=False, key=get_unique_key("use_gemini"))
            
            if use_gemini:
                api_key = st.text_input("Enter Gemini API Key:", type="password", key=get_unique_key("history_api_key"))
                if api_key:
                    parser.api_key = api_key
                    parser.gemini_model = parser.configure_gemini(api_key)
            
            if question:
                with st.spinner("Analyzing your question..."):
                    source, answer = parser.answer_question(question, use_gemini=use_gemini and api_key)
                
                st.markdown(f"**{source}**")
                st.markdown(f"{answer}")
                
                if source == "Basic Response:" and not (use_gemini and api_key):
                    st.info("For more detailed answers, enable Gemini and provide an API key.")
            
            return
    
    for i, report in enumerate(reports):
        with st.expander(f"{report['file_name']} - {report['report_date'].strftime('%Y-%m-%d') if 'report_date' in report else 'Unknown date'}"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"Created: {report['created_at'].strftime('%Y-%m-%d %H:%M')}")
            
            with col2:
                if st.button("View", key=get_unique_key(f"view_{i}")):
                    st.session_state.selected_report_id = report["_id"]
                    st.rerun()
            
            with col3:
                if st.button("Delete", key=get_unique_key(f"delete_{i}")):
                    if db.delete_report(report["_id"], user_id):
                        st.success("Report deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete report.")

def create_streamlit_app():
    if 'processed_file_hash' not in st.session_state:
        st.session_state.processed_file_hash = None
    if 'extraction_results' not in st.session_state:
        st.session_state.extraction_results = []
    if 'extraction_methods' not in st.session_state:
        st.session_state.extraction_methods = []
    if 'test_data' not in st.session_state:
        st.session_state.test_data = None
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = "display"
    if 'report_id' not in st.session_state:
        st.session_state.report_id = None

    if "auth0_check" in st.query_params and st.query_params.get("auth0_check") == "true":
        check_auth0_connection()
        return

    db = BloodReportDatabase()
    
    handle_auth_callback()
    
    render_auth_ui()
    
    with st.sidebar:
        st.markdown("[Auth0 Configuration Check](/app?auth0_check=true)")
    
    if st.session_state.app_mode == "history":
        render_history_page(db)
        return

    st.title("Blood Report Analyzer")
    st.write("Upload your blood test report to analyze and ask questions about your results.")
    
    st.sidebar.header("Settings")
    
    default_api_key = (st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or "")
    api_key_source = st.sidebar.radio(
        "API Key Source", 
        options=["Use from .env file", "Enter manually"],
        index=0 if default_api_key else 1,
        key=get_unique_key("api_key_source")
    )
    
    if api_key_source == "Enter manually":
        api_key = st.sidebar.text_input("Enter Google Gemini API Key", type="password", key=get_unique_key("manual_api_key"))
    else:
        api_key = default_api_key
        if not api_key:
            st.sidebar.warning("No API key found in environment variables. Please check your .env file.")
    
    gemini_models = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-pro",
        "gemini-2.0-pro-exp-02-05"
    ]
    
    selected_model = st.sidebar.selectbox(
        "Select Gemini Model",
        options=gemini_models,
        index=1,
        key=get_unique_key("gemini_model")
    )
    
    use_gemini = st.sidebar.checkbox("Use Gemini for Q&A", value=True if api_key else False, key=get_unique_key("use_gemini_sidebar"))
    
    parser = BloodReportParser(gemini_api_key=api_key if api_key else None, gemini_model_name=selected_model)
    
    if st.session_state.report_id and st.session_state.test_data is not None:
        parser.test_data = st.session_state.test_data
        st.success(f"Viewing saved report (ID: {st.session_state.report_id})")
        
        if st.button("Return to History", key=get_unique_key("return_to_history")):
            switch_to_history_mode()
            st.rerun()
    else:
        uploaded_file = st.file_uploader("Upload blood report (PDF or Image)", type=["pdf", "png", "jpg", "jpeg"], key=get_unique_key("file_uploader"))
        
        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            file_hash = hashlib.md5(file_bytes).hexdigest()
            file_type = uploaded_file.type
            file_name = uploaded_file.name
            
            process_new_file = st.session_state.processed_file_hash != file_hash
            
            if st.session_state.app_mode == "display":
                tab1, tab2, tab3 = st.tabs(["Automatic (Best Results)", "Method Comparison", "Gemini Vision"])
                
                if process_new_file:
                    with tab1:
                        st.write("Processing your report...")
                        
                        st.session_state.extraction_results = []
                        st.session_state.extraction_methods = []
                        
                        extraction_results = []
                        extraction_methods = []
                        
                        if api_key:
                            with st.spinner("Extracting data with Gemini Vision API..."):
                                gemini_results, gemini_message = cached_extract_with_gemini(file_bytes, file_type, api_key, selected_model)
                                if gemini_results is not None and len(gemini_results) > 0:
                                    filtered_gemini = filter_false_positives(gemini_results)
                                    if not filtered_gemini.empty:
                                        extraction_results.append(filtered_gemini)
                                        extraction_methods.append("Gemini Vision")
                                        st.success(f"Successfully extracted {len(filtered_gemini)} test results with Gemini Vision!")
                                    else:
                                        st.warning("Gemini Vision found results but they were filtered out as likely non-test data.")
                                else:
                                    st.warning(f"Gemini Vision extraction unsuccessful: {gemini_message}")
                        
                        ocr_text = ""
                        with st.spinner("Extracting text with OCR for specialized medical extraction..."):
                            try:
                                uploaded_file.seek(0)
                                
                                if file_type == "application/pdf":
                                    ocr_text = parser.extract_text_from_pdf(uploaded_file)
                                else:
                                    image = Image.open(io.BytesIO(file_bytes))
                                    ocr_text = parser.extract_text_from_image(image)
                                    
                                if ocr_text:
                                    with st.spinner("Applying specialized medical extraction..."):
                                        try:
                                            medical_results = parser.extract_specialized_parameters(ocr_text)
                                            if not medical_results.empty:
                                                filtered_medical = filter_false_positives(medical_results)
                                                if not filtered_medical.empty:
                                                    extraction_results.append(filtered_medical)
                                                    extraction_methods.append("Specialized Medical Extraction")
                                                    st.success(f"Successfully extracted {len(filtered_medical)} test results with specialized medical patterns!")
                                                else:
                                                    st.warning("Medical extraction found results but they were filtered out as likely non-test data.")
                                            else:
                                                st.warning("No results found with specialized medical extraction.")
                                        except Exception as e:
                                            st.error(f"Error in specialized extraction: {str(e)}")
                            except Exception as e:
                                st.error(f"Error in OCR processing: {str(e)}")
                        
                        if extraction_results:
                            combined_rows = []
                            added_tests = set()
                            
                            for i, method in enumerate(extraction_methods):
                                df = extraction_results[i]
                                
                                for _, row in df.iterrows():
                                    test_name = row['Test']
                                    if isinstance(test_name, str):
                                        test_name = test_name.replace('*', '').replace('#', '').strip()
                                        row['Test'] = test_name
                                    
                                    test_lower = row['Test'].lower()
                                    
                                    if test_lower not in added_tests:
                                        added_tests.add(test_lower)
                                        row_data = row.copy()
                                        row_data["Source"] = method
                                        combined_rows.append(row_data)
                            
                            if combined_rows:
                                combined_df = pd.DataFrame(combined_rows)
                                combined_df = combined_df.reset_index(drop=True)
                                
                                if any(combined_df.columns.duplicated()):
                                    new_cols = []
                                    seen = {}
                                    for col in combined_df.columns:
                                        if col in seen:
                                            seen[col] += 1
                                            new_cols.append(f"{col}_{seen[col]}")
                                        else:
                                            seen[col] = 0
                                            new_cols.append(col)
                                    combined_df.columns = new_cols
                                
                                cols = ['Test', 'Value', 'Units', 'Reference Range', 'Status', 'Source']
                                
                                for col in cols:
                                    if col not in combined_df.columns:
                                        combined_df[col] = ""
                                
                                parser.test_data = combined_df[cols]

                                st.session_state.processed_file_hash = file_hash
                                st.session_state.extraction_results = extraction_results
                                st.session_state.extraction_methods = extraction_methods
                                st.session_state.test_data = parser.test_data
                                st.session_state.file_name = file_name
                            else:
                                st.error("No valid blood test results could be extracted after filtering.")
                        else:
                            st.error("No valid blood test results could be extracted from your document.")
                else:
                    extraction_results = st.session_state.extraction_results
                    extraction_methods = st.session_state.extraction_methods
                    parser.test_data = st.session_state.test_data
                    with tab1:
                        st.success("Using previously extracted data")
                
                if parser.test_data is not None and not parser.test_data.empty:
                    with tab1:
                        st.subheader("Blood Test Results")
                        st.info(f"Found {len(parser.test_data)} unique test results.")
                        
                        def highlight_status(row):
                            colors = pd.Series([''] * len(row), index=row.index)
                            if row['Status'] == 'High':
                                colors = pd.Series(['background-color: rgba(220, 53, 69, 0.8); color: white'] * len(row), index=row.index)
                            elif row['Status'] == 'Low':
                                colors = pd.Series(['background-color: rgba(255, 193, 7, 0.8); color: black'] * len(row), index=row.index)
                            return colors
                        
                        display_data = parser.test_data.reset_index(drop=True)
                        st.dataframe(display_data.style.apply(highlight_status, axis=1))
                        
                        if get_auth_status():
                            st.subheader("Save This Report")
                            user_id = st.session_state.auth_user.get('sub')
                            save_current_report(db, user_id, parser.test_data, file_name)
                        else:
                            st.info("Login to save this report and access it later.")
                        
                        st.subheader("EHR Style Visualization")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### Normal Results")
                            normal = parser.test_data[parser.test_data["Status"] == "Normal"]
                            if len(normal) > 0:
                                for _, row in normal.iterrows():
                                    st.markdown(f"✅ **{row['Test']}**: {row['Value']} {row['Units']}")
                            else:
                                st.write("No normal results found.")
                        
                        with col2:
                            st.markdown("#### Abnormal Results")
                            abnormal = parser.test_data[parser.test_data["Status"] != "Normal"]
                            if len(abnormal) > 0:
                                for _, row in abnormal.iterrows():
                                    if row['Status'] == "High":
                                        st.markdown(f"""
                                        <div style="padding: 10px; border-radius: 5px; margin-bottom: 10px; 
                                        background-color: rgba(220, 53, 69, 0.2); border-left: 4px solid #dc3545;">
                                        <span style="color: #dc3545; font-weight: bold;">↑ {row['Test']}</span>: {row['Value']} {row['Units']} 
                                        <br/><small>Reference range: {row['Reference Range']}</small>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div style="padding: 10px; border-radius: 5px; margin-bottom: 10px; 
                                        background-color: rgba(255, 193, 7, 0.2); border-left: 4px solid #ffc107;">
                                        <span style="color: #ffc107; font-weight: bold;">↓ {row['Test']}</span>: {row['Value']} {row['Units']} 
                                        <br/><small>Reference range: {row['Reference Range']}</small>
                                        </div>
                                        """, unsafe_allow_html=True)
                            else:
                                st.write("No abnormal results found.")
                    
                    with tab2:
                        st.subheader("Method Comparison")
                        
                        if not extraction_results:
                            st.warning("No extraction results available for comparison.")
                        elif len(extraction_results) < 2:
                            st.warning("Only one extraction method was successful. No comparison possible.")
                            
                            method = extraction_methods[0]
                            st.write(f"Results from {method}:")
                            st.dataframe(extraction_results[0])
                        else:
                            all_tests = set()
                            for df in extraction_results:
                                all_tests.update(df['Test'].str.lower())
                            
                            comparison_data = []
                            
                            for test_name in sorted(all_tests):
                                row_data = {"Test": test_name.title()}
                                
                                for i, method in enumerate(extraction_methods):
                                    df = extraction_results[i]
                                    matches = df[df['Test'].str.lower() == test_name]
                                    
                                    if len(matches) > 0:
                                        value = matches.iloc[0]['Value']
                                        units = matches.iloc[0]['Units']
                                        row_data[method] = f"{value} {units}"
                                    else:
                                        row_data[method] = "Not found"
                                
                                comparison_data.append(row_data)
                            
                            comparison_df = pd.DataFrame(comparison_data)
                            
                            st.write("Comparison of extraction methods:")
                            st.dataframe(comparison_df)
                            
                            st.subheader("Method Statistics")
                            
                            common_tests = sum(1 for row in comparison_data 
                                            if all("Not found" not in str(row.get(method, "")) 
                                                    for method in extraction_methods))
                            
                            for i, method in enumerate(extraction_methods):
                                unique_tests = sum(1 for row in comparison_data 
                                                if row.get(method, "") != "Not found" 
                                                and any(row.get(other, "") == "Not found" 
                                                        for j, other in enumerate(extraction_methods) if j != i))
                                
                                st.info(f"📊 {method}: Found {len(extraction_results[i])} tests in total")
                                st.info(f"🔍 {method}: Found {unique_tests} tests not detected by other methods")
                            
                            st.success(f"✅ {common_tests} tests were found by ALL extraction methods")
                    
                    with tab3:
                        if api_key:
                            st.subheader("Gemini Vision Extraction Details")
                            
                            gemini_index = None
                            for i, method in enumerate(extraction_methods):
                                if method == "Gemini Vision":
                                    gemini_index = i
                                    break
                            
                            if gemini_index is not None and not process_new_file:
                                gemini_results = extraction_results[gemini_index]
                                st.success(f"Showing previously extracted Gemini Vision results ({len(gemini_results)} tests found).")
                                
                                filtered_results = filter_false_positives(gemini_results)
                                
                                raw_tab, filtered_tab, removed_tab = st.tabs(["Raw Extraction", "Filtered Results", "Filtered Out"])
                                
                                with raw_tab:
                                    st.write("All data extracted by Gemini before filtering:")
                                    st.dataframe(gemini_results)
                                
                                with filtered_tab:
                                    if not filtered_results.empty:
                                        st.write(f"Data after filtering ({len(filtered_results)} tests):")
                                        st.dataframe(filtered_results)
                                    else:
                                        st.warning("All extracted data was filtered out as likely non-test data.")
                                
                                with removed_tab:
                                    if len(filtered_results) < len(gemini_results):
                                        removed = gemini_results[~gemini_results['Test'].isin(filtered_results['Test'])]
                                        st.write(f"Data removed by filtering ({len(removed)} items):")
                                        st.dataframe(removed)
                                    else:
                                        st.success("No data was filtered out.")
                            else:
                                with st.spinner("Extracting with Gemini Vision..."):
                                    gemini_results, gemini_message = cached_extract_with_gemini(
                                        file_bytes, 
                                        file_type,
                                        api_key,
                                        selected_model
                                    )
                                    if gemini_results is not None and not gemini_results.empty:
                                        st.success(f"Gemini Vision found {len(gemini_results)} test results.")
                                        
                                        filtered_results = filter_false_positives(gemini_results)
                                        
                                        raw_tab, filtered_tab, removed_tab = st.tabs(["Raw Extraction", "Filtered Results", "Filtered Out"])
                                        
                                        with raw_tab:
                                            st.write("All data extracted by Gemini before filtering:")
                                            st.dataframe(gemini_results)
                                        
                                        with filtered_tab:
                                            if not filtered_results.empty:
                                                st.write(f"Data after filtering ({len(filtered_results)} tests):")
                                                st.dataframe(filtered_results)
                                            else:
                                                st.warning("All extracted data was filtered out as likely non-test data.")
                                        
                                        with removed_tab:
                                            if len(filtered_results) < len(gemini_results):
                                                removed = gemini_results[~gemini_results['Test'].isin(filtered_results['Test'])]
                                                st.write(f"Data removed by filtering ({len(removed)} items):")
                                                st.dataframe(removed)
                                            else:
                                                st.success("No data was filtered out.")
                                    else:
                                        st.error(f"Gemini Vision extraction failed: {gemini_message}")
                        else:
                            st.warning("Gemini Vision extraction requires an API key. Please enter it in the sidebar.")
                    
                    st.markdown("---")
                    st.subheader("Ask Questions About Your Results")
                    st.button("Switch to Q&A Mode", on_click=switch_to_qa_mode, key=get_unique_key("switch_to_qa_mode"))
                    
            elif st.session_state.app_mode == "qa":
                parser.test_data = st.session_state.test_data
                
                st.subheader("Ask Questions About Your Results")
                st.info(f"Using extracted data from {len(parser.test_data)} tests - No OCR needed")
                
                if st.button("← Back to Results", key=get_unique_key("back_to_results")):
                    switch_to_display_mode()
                    st.rerun()
                
                question = st.text_input("Enter your question:", key=get_unique_key("question_input"))
                
                if question:
                    with st.spinner("Analyzing your question..."):
                        source, answer = answer_question_with_data(
                            parser,
                            question, 
                            use_gemini=use_gemini
                        )
                    
                    st.markdown(f"**{source}**")
                    st.markdown(f"{answer}")
                    
                    if source == "Basic Response:" and not use_gemini and not api_key:
                        st.info("For more detailed answers, try enabling the Gemini model by entering your API key in the sidebar.")
        else:
            st.info("Please upload a blood test report to get started.")

if __name__ == "__main__":
    create_streamlit_app()