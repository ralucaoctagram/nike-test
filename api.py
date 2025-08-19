import streamlit as st
import pandas as pd
import zipfile
import os
from PIL import Image
from io import BytesIO

st.title("📊 Banner Checker")

# Step 1: Upload Excel
excel_file = st.file_uploader("Upload Excel file", type=["xlsx"])
# Step 2: Upload ZIP archive
zip_file = st.file_uploader("Upload Banners ZIP", type=["zip"])
# Step 3: API key input (hidden, per session)
api_key = st.text_input("Enter API Key", type="password")

if excel_file and zip_file:
    st.success("✅ Files uploaded successfully!")

    # Extract ZIP in memory
    with zipfile.ZipFile(zip_file, "r") as zip_ref:
        file_list = zip_ref.namelist()
        st.write(f"Found **{len(file_list)} banners** in archive")

        # Example: Check real image sizes
        for file in file_list:
            if file.lower().endswith((".png", ".jpg", ".jpeg")):
                with zip_ref.open(file) as f:
                    img = Image.open(BytesIO(f.read()))
                    width, height = img.size
                    st.write(f"{file} → {width}x{height}")
