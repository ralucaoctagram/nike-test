import streamlit as st
import pandas as pd
import zipfile
import os
from PIL import Image
from io import BytesIO
import re
import tempfile
import google.generativeai as genai

st.set_page_config(page_title="Banner Validator", layout="wide")
st.title("📊 Banner Validator")
st.write(
    "Încarcă arhiva cu bannere și fișierul Excel pentru a valida structura, dimensiunile și traducerile."
)

# --- Pasul 1: Încărcare fișiere ---
api_key = st.text_input("🔑 Introdu Cheia API Gemini:", type="password")
excel_file = st.file_uploader("📑 Încarcă fișierul Excel cu traducerile", type=["xlsx"])
zip_file = st.file_uploader("🗂️ Încarcă arhiva cu bannere (ZIP)", type=["zip"])

if zip_file:
    st.success("✅ Arhiva ZIP cu bannere a fost încărcată cu succes!")

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
            st.success("✅ Arhiva a fost dezarhivată.")

        root_folders = [f.name for f in os.scandir(temp_dir) if f.is_dir() and f.name != '__MACOSX']
        en_path = next((os.path.join(temp_dir, folder) for folder in root_folders if folder.lower() == 'en'), None)
        
        if en_path:
            en_banners = []
            for root, dirs, files in os.walk(en_path):
                if '__MACOSX' in dirs:
                    dirs.remove('__MACOSX')
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        en_banners.append(os.path.relpath(os.path.join(root, file), en_path))
            
            # --- Validare Structură și Dimensiuni ---
            st.subheader("📁 Validare Structură Foldere și Fișiere")
            validation_data = {banner: {lang: "✅ Găsit" if os.path.exists(os.path.join(temp_dir, lang, banner)) else "❌ Lipsește" for lang in root_folders} for banner in en_banners}
            st.dataframe(pd.DataFrame(validation_data).T)

            st.subheader("🖼️ Validare Dimensiuni Bannere")
            size_results = []
            en_banner_sizes = {rel_path: (Image.open(os.path.join(en_path, rel_path)).size if os.path.exists(os.path.join(en_path, rel_path)) else ("Eroare", "Eroare")) for rel_path in en_banners}
            for relative_path in en_banners:
                expected_size = en_banner_sizes.get(relative_path)
                for lang in root_folders:
                    full_path = os.path.join(temp_dir, lang, relative_path)
                    if os.path.exists(full_path):
                        try:
                            actual_size = Image.open(full_path).size
                        except Exception:
                            actual_size = ("Eroare", "Eroare")
                        status = "✅ Dimensiune corectă" if actual_size == expected_size else "❌ Dimensiune incorectă"
                        
                        match = re.search(r"(\d+)x(\d+)", relative_path)
                        declared_size_1x = f"{match.group(1)}x{match.group(2)}" if match else "N/A"
                        size_results.append({"Limbă": lang, "Cale Banner": relative_path, "Dimensiune Declarată (1x)": declared_size_1x, "Dimensiune Așteptată": f"{expected_size[0]}x{expected_size[1]}", "Dimensiune Reală": f"{actual_size[0]}x{actual_size[1]}", "Status": status})
            st.dataframe(pd.DataFrame(size_results))

            # --- Pasul 4: Validare Traduceri (cu buton) ---
            st.markdown("---")
            st.subheader("⚡ Validare Traduceri cu Gemini API")
            if excel_file and api_key and st.button("🚀 Validează traducerile"):
                with st.spinner('Validating translations...'):
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
                    xl = pd.ExcelFile(excel_file)
                    sheets_df = {sheet: xl.parse(sheet, header=0) for sheet in xl.sheet_names}
                    
                    translation_results = []
                    for relative_path in en_banners:
                        en_path_full = os.path.join(en_path, relative_path)
                        if not os.path.exists(en_path_full): continue

                        try:
                            with open(en_path_full, "rb") as f:
                                en_image_data = f.read()
                            en_text_extracted = model.generate_content(["Extract all text from the image.", {"mime_type": "image/jpeg", "data": en_image_data}]).text
                        except Exception as e:
                            en_text_extracted = None
                            st.warning(f"Eroare OCR pentru {relative_path} (EN): {e}")

                        if not en_text_extracted: continue
                        
                        expected_row = next((row for df in sheets_df.values() for _, row in df.iterrows() if any(en_text_extracted.strip() in str(cell).strip() for cell in row)), None)
                        if expected_row is None:
                            st.warning(f"Textul '{en_text_extracted.strip()}' din bannerul EN ({relative_path}) nu a fost găsit în Excel.")
                            continue

                        for lang in root_folders:
                            lang_path_full = os.path.join(temp_dir, lang, relative_path)
                            if os.path.exists(lang_path_full):
                                try:
                                    with open(lang_path_full, "rb") as f:
                                        lang_image_data = f.read()
                                    lang_text_extracted = model.generate_content(["Extract all text from the image.", {"mime_type": "image/jpeg", "data": lang_image_data}]).text
                                except Exception as e:
                                    lang_text_extracted = None
                                    st.warning(f"Eroare OCR pentru {relative_path} ({lang}): {e}")
                                
                                expected_text = str(expected_row.get(lang.strip(), "")).strip()
                                
                                status = "✅ PASS" if lang_text_extracted and lang_text_extracted.strip() == expected_text else "❌ FAIL"
                                translation_results.append({"Banner": relative_path, "Language": lang, "Expected Text": expected_text, "Extracted Text": lang_text_extracted, "Status": status})
                    
                    st.success("✅ Verificare completă!")
                    if translation_results:
                        st.dataframe(pd.DataFrame(translation_results))
                    else:
                        st.info("Niciun banner nu a putut fi verificat.")
            elif excel_file or api_key:
                st.info("Apasă pe butonul de mai jos pentru a începe validarea traducerilor.")
        else:
            st.error("Folderul 'en' (limba engleză) nu a fost găsit în arhivă.")
