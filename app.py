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

# --- Pasul 1: Introducerea cheii API ---
api_key = st.text_input("🔑 Introdu Cheia API Gemini:", type="password")

# --- Pasul 2: Încărcare Excel ---
excel_file = st.file_uploader("📑 Încarcă fișierul Excel cu traducerile", type=["xlsx"])

# --- Pasul 3: Încărcare Arhivă ZIP ---
zip_file = st.file_uploader("🗂️ Încarcă arhiva cu bannere (ZIP)", type=["zip"])

if zip_file:
    st.success("✅ Arhiva ZIP cu bannere a fost încărcată cu succes!")

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
            st.success("✅ Arhiva a fost dezarhivată.")

        root_folders = [f.name for f in os.scandir(temp_dir) if f.is_dir() and f.name != '__MACOSX']
        
        en_path = None
        for folder in root_folders:
            if folder.lower() == 'en':
                en_path = os.path.join(temp_dir, folder)
                break
        
        if en_path:
            en_banners = []
            for root, dirs, files in os.walk(en_path):
                if '__MACOSX' in dirs:
                    dirs.remove('__MACOSX')
                
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        relative_path = os.path.relpath(os.path.join(root, file), en_path)
                        en_banners.append(relative_path)
            
            # --- Validarea structurii de foldere și fișiere ---
            st.subheader("📁 Validare Structură Foldere și Fișiere")
            validation_data = {banner: {} for banner in en_banners}
            
            for banner_path in en_banners:
                for lang in root_folders:
                    full_path_lang = os.path.join(temp_dir, lang, banner_path)
                    validation_data[banner_path][lang] = "✅ Găsit" if os.path.exists(full_path_lang) else "❌ Lipsește"
            
            df_structure = pd.DataFrame(validation_data).T
            st.dataframe(df_structure)

            # --- Validarea Dimensiunilor Bannerelor ---
            st.subheader("🖼️ Validare Dimensiuni Bannere")
            size_results = []
            
            # Obținem dimensiunile reale ale bannerelor EN pentru referință
            en_banner_sizes = {}
            for relative_path in en_banners:
                en_file_path = os.path.join(en_path, relative_path)
                try:
                    with Image.open(en_file_path) as img:
                        en_banner_sizes[relative_path] = img.size
                except Exception as e:
                    en_banner_sizes[relative_path] = ("Eroare", "Eroare")

            # Verificăm fiecare banner din fiecare limbă
            for relative_path in en_banners:
                expected_size = en_banner_sizes.get(relative_path)
                if expected_size:
                    for lang in root_folders:
                        full_path = os.path.join(temp_dir, lang, relative_path)
                        if os.path.exists(full_path):
                            try:
                                with Image.open(full_path) as img:
                                    actual_size = img.size
                            except Exception:
                                actual_size = ("Eroare", "Eroare")

                            match = re.search(r"(\d+)x(\d+)", relative_path)
                            declared_size_1x = f"{match.group(1)}x{match.group(2)}" if match else "N/A"
                            
                            status = "✅ Dimensiune corectă" if actual_size == expected_size else "❌ Dimensiune incorectă"
                            
                            size_results.append({
                                "Limbă": lang,
                                "Cale Banner": relative_path,
                                "Dimensiune Declarată (1x)": declared_size_1x,
                                "Dimensiune Așteptată": f"{expected_size[0]}x{expected_size[1]}",
                                "Dimensiune Reală": f"{actual_size[0]}x{actual_size[1]}",
                                "Status": status
                            })
            
            df_sizes = pd.DataFrame(size_results)
            st.dataframe(df_sizes)

        else:
            st.error("Folderul 'en' (limba engleză) nu a fost găsit în arhivă.")

# --- Spațiu pentru Validarea Traducerilor ---
st.markdown("---")
st.subheader("⚡ Următorul Pas: Validarea Traducerilor")
st.write(
    """
    Pentru a continua, încarcă fișierul Excel și introdu cheia API Gemini mai sus. Odată ce ambele sunt furnizate, aplicația va efectua OCR pe bannere și va verifica textul cu traducerile din fișierul Excel.
    """
)
