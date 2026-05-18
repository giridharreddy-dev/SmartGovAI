import streamlit as st
import pdfplumber

st.title("SmartGov AI")

uploaded_file = st.file_uploader(
    "Upload Healthcare Scheme PDF",
    type=["pdf"]
)

if uploaded_file is not None:

    st.success("File uploaded successfully!")

    text = ""

    with pdfplumber.open(uploaded_file) as pdf:

        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text

    st.subheader("Extracted Text")
    st.write(text)
