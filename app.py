import streamlit as st

st.title("SmartGov AI")

uploaded_file = st.file_uploader(
    "Upload Healthcare Scheme PDF",
    type=["pdf"]
)

if uploaded_file is not None:
    st.success("File uploaded successfully!")
    st.write("Filename:", uploaded_file.name)