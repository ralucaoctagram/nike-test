import streamlit as st
import pandas as pd
import zipfile
import os
from PIL import Image
from io import BytesIO
import re
import tempfile
import base64
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

def normalize_text(text):
    """Normalize text for a more flexible comparison."""
    if not isinstance(text, str):
        return ""
    return re.sub(r'\s+', ' ', text).strip().lower()

def get_ocr_text(image_data, model):
    """Extract a single block of text from an image."""
    try:
        response = model.generate_content([
            "Extract all text from the image, preserving the original line breaks.",
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        if response.text:
            return response.text
        return ""
    except Exception as e:
        st.warning(f"Eroare OCR: {e}")
        return ""

if zip_file:
    st.success("✅ Arhiva ZIP cu bannere a fost încărcată cu succes!")

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
            st.success("✅ Arhiva a fost dezarhivată.")

        root_folders = [f.name for f in os.scandir(temp_dir) if f.is_dir() and f.name.upper() != '__MACOSX']
        en_folder = next((f for f in root_folders if f.lower() == 'en'), None)
        
        if en_folder:
            en_path = os.path.join(temp_dir, en_folder)
            en_banners = []
            for root, dirs, files in os.walk(en_path):
                if '__MACOSX' in dirs: dirs.remove('__MACOSX')
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        en_banners.append(os.path.relpath(os.path.join(root, file), en_path))
            
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
                        try: actual_size = Image.open(full_path).size
                        except Exception: actual_size = ("Eroare", "Eroare")
                        status = "✅ Dimensiune corectă" if actual_size == expected_size else "❌ Dimensiune incorectă"
                        match = re.search(r"(\d+)x(\d+)", relative_path)
                        declared_size_1x = f"{match.group(1)}x{match.group(2)}" if match else "N/A"
                        size_results.append({"Limbă": lang, "Cale Banner": relative_path, "Dimensiune Declarată (1x)": declared_size_1x, "Dimensiune Așteptată": f"{expected_size[0]}x{expected_size[1]}", "Dimensiune Reală": f"{actual_size[0]}x{actual_size[1]}", "Status": status})
            st.dataframe(pd.DataFrame(size_results))
            
            st.markdown("---")
            st.subheader("⚡ Validare Traduceri Manuală")
            if excel_file and api_key:
                st.info("Te rog să introduci numărul liniei din Excel care corespunde fiecărui banner EN.")
                
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                except Exception as e:
                    st.error(f"Eroare la configurarea Gemini API: {e}. Verifică cheia API.")
                    st.stop()
                
                try:
                    excel_df = pd.read_excel(excel_file, header=0, dtype=str).fillna('')
                    st.write("Preview Excel:")
                    st.dataframe(excel_df.head(5))
                except Exception as e:
                    st.error(f"Eroare la citirea fișierului Excel: {e}")
                    st.stop()
                
                # Colectează inputurile de la utilizator
                user_inputs = {}
                for relative_path in en_banners:
                    en_full_path = os.path.join(en_path, relative_path)
                    st.markdown(f"**Banner:** `{relative_path}`")
                    st.image(en_full_path, width=200)
                    
                    try:
                        with open(en_full_path, "rb") as f:
                            en_image_data = f.read()
                        en_ocr_text = get_ocr_text(en_image_data, model)
                        st.text_area(f"Text extras de OCR (pentru referință):", en_ocr_text, height=150, key=f"ocr_{relative_path}")
                    except Exception as e:
                        st.warning(f"Eroare OCR pentru {relative_path}: {e}")
                    
                    user_inputs[relative_path] = st.text_input(f"Introdu numerele de rând din Excel (separate prin virgulă) care corespund textelor de mai sus:", key=f"input_{relative_path}", placeholder="ex: 2, 5, 8")
                
                if st.button("🚀 Validează traducerile"):
                    with st.spinner('Validating translations...'):
                        st.subheader("🔍 Raport Detaliat de Validare a Traducerilor")
                        for relative_path in en_banners:
                            st.markdown(f"### Banner: `{relative_path}`")
                            
                            row_numbers_str = user_inputs.get(relative_path, "")
                            if not row_numbers_str:
                                st.warning(f"Nu ai introdus numere de rând pentru bannerul {relative_path}.")
                                continue
                            
                            try:
                                row_indices = [int(n) - 1 for n in row_numbers_str.split(',')]
                                en_text_rows = excel_df.iloc[row_indices]
                            except Exception as e:
                                st.error(f"Eroare la citirea rândurilor din Excel: {e}")
                                continue
                            
                            for lang in root_folders:
                                st.markdown(f"#### Limbă: `{lang}`")
                                
                                expected_texts_by_lang = [str(row.get(lang.strip(), "")).strip() for _, row in en_text_rows.iterrows()]
                                
                                lang_path_full = os.path.join(temp_dir, lang, relative_path)
                                extracted_text = ""
                                if os.path.exists(lang_path_full):
                                    st.image(lang_path_full, width=200)
                                    extracted_text = get_ocr_text(lang_image_data, model)
                                else:
                                    st.warning(f"Fișierul ({lang}) nu a fost găsit.")

                                cols = st.columns(2)
                                with cols[0]:
                                    st.markdown("##### Expected Text")
                                    st.markdown("---")
                                    for text in expected_texts_by_lang:
                                        st.markdown(f"- `{text}`")
                                with cols[1]:
                                    st.markdown("##### Extracted Text")
                                    st.markdown("---")
                                    if extracted_text:
                                        st.write(extracted_text.strip())
                                    else:
                                        st.write("N/A")

                                all_passed = True
                                for expected_text in expected_texts_by_lang:
                                    if normalize_text(expected_text) not in normalize_text(extracted_text):
                                        all_passed = False
                                        break
                                
                                if all_passed:
                                    st.success("✅ Toate textele corespund!")
                                else:
                                    st.error("❌ Există nepotriviri!")

                                st.markdown("---")
            else:
                st.info("Apasă pe butonul de mai jos pentru a începe validarea traducerilor.")
        else:
            st.error("Folderul 'en' (limba engleză) nu a fost găsit în arhivă.")
