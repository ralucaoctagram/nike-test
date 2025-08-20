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

# Initialize session state for user inputs
if 'user_inputs' not in st.session_state:
    st.session_state.user_inputs = {}

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
    """Extracts a single block of text from an image."""
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

def get_text_preview(row_numbers_str, excel_df_raw):
    """Generates a text preview for the given row numbers."""
    preview_text = ""
    if row_numbers_str:
        try:
            row_indices = [int(n) - 1 for n in row_numbers_str.split('\n') if n.strip().isdigit()]
            for index in row_indices:
                if 0 <= index < len(excel_df_raw):
                    row_data = " | ".join(excel_df_raw.iloc[index].tolist())
                    preview_text += f"Linia {index + 1}: {row_data}\n"
                else:
                    preview_text +=
