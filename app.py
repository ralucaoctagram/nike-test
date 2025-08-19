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

        # Obținerea tuturor folderelor de la rădăcină (coduri de limbă)
        # Ignoră folderele __MACOSX
        root_folders = [f.name for f in os.scandir(temp_dir) if f.is_dir() and f.name != '__MACOSX']
        
        en_path = None
        for folder in root_folders:
            if folder.lower() == 'en':
                en_path = os.path.join(temp_dir, folder)
                break
        
        if en_path:
            # Găsirea tuturor bannerelor din folderul 'en' ca sursă de adevăr
            en_banners = []
            for root, dirs, files in os.walk(en_path):
                # Omiterea directorului __MACOSX
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
            for relative_path in en_banners:
                en_file_path = os.path.join(en_path, relative_path)
                
                try:
                    with Image.open(en_file_path) as img:
                        width, height = img.size
                except Exception as e:
                    width, height = "Eroare", "Eroare"

                match = re.search(r"(\d+)x(\d+)", relative_path)
                if match:
                    declared_w_1x, declared_h_1x = int(match.group(1)), int(match.group(2))
                    expected_w_2x, expected_h_2x = declared_w_1x * 2, declared_h_1x * 2
                    
                    status = ""
                    if width == expected_w_2x and height == expected_h_2x:
                        status = "✅ Dimensiune corectă (2x)"
                    else:
                        status = "❌ Dimensiune incorectă"
                    
                    size_results.append({
                        "Cale Banner": relative_path,
                        "Dimensiune Declarată (1x)": f"{declared_w_1x}x{declared_h_1x}",
                        "Dimensiune Așteptată (2x)": f"{expected_w_2x}x{expected_h_2x}",
                        "Dimensiune Reală": f"{width}x{height}",
                        "Status": status
                    })
                else:
                    size_results.append({
                        "Cale Banner": relative_path,
                        "Dimensiune Declarată (1x)": "N/A",
                        "Dimensiune Așteptată (2x)": "N/A",
                        "Dimensiune Reală": f"{width}x{height}",
                        "Status": "⚠️ Dimensiune nedeclarată în nume"
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
