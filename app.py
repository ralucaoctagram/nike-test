import streamlit as st
import pandas as pd
import zipfile
import os
from PIL import Image
from io import BytesIO
import re

st.set_page_config(page_title="Banner Translation Validator", layout="wide")
st.title("📊 Banner Translation Validator")
st.write(
    "Upload your translation Excel file and banner archive to automatically validate text accuracy across different languages and campaigns."
)

# --- Step 1: API Key Input (secure, per session) ---
api_key = st.text_input("🔑 Enter Gemini API Key:", type="password")

# --- Step 2: Upload Excel ---
excel_file = st.file_uploader("📑 Upload Excel File", type=["xlsx"])

if excel_file:
    st.success("✅ Excel uploaded successfully!")
    xl = pd.ExcelFile(excel_file)
    st.write(f"Found {len(xl.sheet_names)} Campaign Tabs:")
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        langs = list(df.columns)
        st.write(f"**{sheet}** → Languages: {len(langs)} ({', '.join(langs)})")
        st.dataframe(df.head(5))

# --- Step 3: Upload ZIP Archive ---
zip_file = st.file_uploader("🗂️ Upload Banner Archive (ZIP)", type=["zip"])

if zip_file:
    st.success("✅ Banner ZIP uploaded successfully!")

    # Extract ZIP in memory
    with zipfile.ZipFile(zip_file, "r") as zip_ref:
        file_list = zip_ref.namelist()
        st.write(f"Found **{len(file_list)} banners** in archive")

        results = []

        for file in file_list:
            if file.lower().endswith((".png", ".jpg", ".jpeg")):
                with zip_ref.open(file) as f:
                    img = Image.open(BytesIO(f.read()))
                    width, height = img.size

                # Extract declared size from filename (e.g., Dark_728x90.jpg)
                match = re.search(r"(\d+)x(\d+)", file)
                if match:
                    declared_w, declared_h = int(match.group(1)), int(match.group(2))
                    status = (
                        "✅ Correct 2x"
                        if (width == declared_w * 2 and height == declared_h * 2)
                        else "❌ Incorrect 2x"
                    )
                else:
                    declared_w, declared_h = None, None
                    status = "⚠️ No size found in filename"

                results.append(
                    [file, f"{declared_w}x{declared_h}" if declared_w else "?", f"{width}x{height}", status]
                )

        st.subheader("📊 Banner Size Verification")
        st.dataframe(pd.DataFrame(results, columns=["Banner Path", "Declared Size", "Real Size", "Status"]))

# --- Placeholder for OCR / Translation Validation ---
st.markdown("---")
st.subheader("⚡ Next Steps / Future Enhancements")
st.write(
    """
    - Map EN banners as reference for each campaign
    - Compare folder structure of other languages (missing banners)
    - OCR banners using Gemini API and cross-check against Excel translations
    - Generate downloadable report (CSV/Excel)
    """
)
