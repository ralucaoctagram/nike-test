import streamlit as st
import pandas as pd
import zipfile
import os
from PIL import Image
from io import BytesIO
import re
import tempfile
import google.generativeai as genai

st.set_page_config(page_title="Banner Translation Validator", layout="wide")
st.title("📊 Banner Translation Validator")
st.write(
    "Upload your translation Excel file and banner archive to automatically validate text accuracy across different languages and campaigns."
)

# --- Step 1: API Key Input (secure, per session) ---
api_key = st.text_input("🔑 Enter Gemini API Key:", type="password")

def perform_ocr(image_data):
    """Performs OCR on an image using the Gemini API."""
    try:
        if not api_key:
            st.error("Please enter a Gemini API Key.")
            return None
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        
        response = model.generate_content([
            "Extract all text from the image.",
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        
        return response.text
    except Exception as e:
        st.error(f"OCR failed: {e}")
        return None

# --- Step 2: Upload Excel ---
excel_file = st.file_uploader("📑 Upload Excel File", type=["xlsx"])

# --- Step 3: Upload ZIP Archive ---
zip_file = st.file_uploader("🗂️ Upload Banner Archive (ZIP)", type=["zip"])

if api_key and excel_file and zip_file:
    st.success("✅ Files and API Key uploaded successfully! Starting validation...")

    # Load Excel data
    xl = pd.ExcelFile(excel_file)
    sheets_df = {sheet: xl.parse(sheet, header=None) for sheet in xl.sheet_names}
    
    # Extract ZIP into a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
            st.success(f"✅ Banner archive extracted to temporary directory.")

        # Dictionary to store all banners, grouped by their relative path and language
        banners = {}
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Determine language code from the parent folder
                language_code = os.path.basename(os.path.dirname(os.path.dirname(file_path))).lower()
                
                # Get the path relative to the language folder (e.g., 'campaign1/banner_1.png')
                relative_path = os.path.relpath(file_path, os.path.join(temp_dir, language_code))
                
                if relative_path not in banners:
                    banners[relative_path] = {}
                banners[relative_path][language_code] = file_path

        translation_results = []

        # Start the validation process
        st.subheader("🤖 OCR and Translation Verification")
        if 'en' in banners.get(next(iter(banners)), {}): # Check if EN banners exist
            for relative_path, file_paths in banners.items():
                if 'en' in file_paths:
                    en_path = file_paths['en']
                    st.info(f"Processing EN banner: {relative_path}")
                    with open(en_path, "rb") as f:
                        en_image_data = f.read()

                    # Perform OCR on EN banner
                    en_text_extracted = perform_ocr(en_image_data)
                    
                    if not en_text_extracted:
                        continue
                    
                    st.write(f"EN OCR Text: **{en_text_extracted.strip()}**")
                    
                    # Find the correct translation row in the Excel sheets
                    expected_row = None
                    for campaign, df in sheets_df.items():
                        for index, row in df.iterrows():
                            if en_text_extracted.strip() in [str(x).strip() for x in row.values]:
                                expected_row = row
                                break
                        if expected_row is not None:
                            break

                    if expected_row is None:
                        st.warning(f"Could not find a matching row in any Excel sheet for EN banner: {relative_path}")
                        continue
                    
                    # Verify other languages
                    for lang, lang_path in file_paths.items():
                        if lang != 'en':
                            st.write(f"  → Checking {lang} banner...")
                            with open(lang_path, "rb") as f:
                                lang_image_data = f.read()
                            
                            lang_text_extracted = perform_ocr(lang_image_data)
                            
                            expected_text = str(expected_row.get(lang.strip(), "")).strip()
                            status = "✅ Pass" if lang_text_extracted and lang_text_extracted.strip() == expected_text else "❌ Fail"
                            notes = f"Expected: '{expected_text}', Found: '{lang_text_extracted}'" if status == "❌ Fail" else ""
                            
                            translation_results.append({
                                'Campaign/Banner': relative_path,
                                'Language': lang,
                                'Status': status,
                                'Notes': notes
                            })
        else:
            st.error("The 'en' (English) language folder was not found in the archive.")
            
        st.markdown("---")
        st.subheader("Final Translation Report")
        if translation_results:
            results_df = pd.DataFrame(translation_results)
            st.dataframe(results_df)
        else:
            st.warning("No banners were verified. Please check the uploaded files and folder structure.")
