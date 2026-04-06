import streamlit as st
import pandas as pd

st.set_page_config(page_title="Mass Balance", layout="wide")

st.title("📊 Mass Balance Data Manager")
st.markdown("Upload your SysCAD Excel export here. The engine will parse and stage the data for equipment sizing.")

# --- 1. File Upload Section ---
uploaded_file = st.file_uploader("Upload SysCAD Output (Excel)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.info("File uploaded! (We will connect the data parser in the next step).")

# --- 2. Data Preview Section ---
st.markdown("---")
st.subheader("Current Active Mass Balance")

# Check if we have data in memory
if 'mass_balance' in st.session_state:
    df_display = st.session_state['mass_balance']
    st.write(f"**Loaded Streams:** {len(df_display)} | **Tracked Properties:** {len(df_display.columns)}")
    st.dataframe(df_display, use_container_width=True)
else:
    st.info("No mass balance loaded. Please upload a file above.")
