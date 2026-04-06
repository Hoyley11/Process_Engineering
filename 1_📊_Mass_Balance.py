# pages/1_📊_Mass_Balance.py
import streamlit as st
import pandas as pd
from utils.data_parser import parse_syscad_mass_balance
from utils.data_manager import DATA_DIR # Reusing our manager

st.title("Mass Balance Data Manager")
st.markdown("Upload your SysCAD Excel export here. The engine will parse and stage the data for equipment sizing.")

# --- 1. File Upload Section ---
uploaded_file = st.file_uploader("Upload SysCAD Output (Excel)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    with st.spinner("Parsing SysCAD data..."):
        # Run our custom parser
        df_parsed = parse_syscad_mass_balance(uploaded_file)
        
        if df_parsed is not None:
            st.success("File parsed successfully!")
            
            # Save to Streamlit memory for fast access across pages
            st.session_state['mass_balance'] = df_parsed
            
            # Also save a flat CSV backup for reference/debugging
            backup_path = DATA_DIR / "current_mass_balance.csv"
            df_parsed.to_csv(backup_path)

# --- 2. Data Preview Section ---
st.markdown("---")
st.subheader("Current Active Mass Balance")

# Check if we have data in memory
if 'mass_balance' in st.session_state:
    df_display = st.session_state['mass_balance']
    
    st.write(f"**Loaded Streams:** {len(df_display)} | **Tracked Properties:** {len(df_display.columns)}")
    
    # Interactive dataframe view
    st.dataframe(df_display, use_container_width=True)
    
    # Quick Lookup Tool for debugging
    st.markdown("### Stream Quick-Lookup")
    stream_to_check = st.selectbox("Select a stream to view properties:", df_display.index)
    if stream_to_check:
        st.json(df_display.loc[stream_to_check].dropna().to_dict())
else:
    st.info("No mass balance loaded. Please upload a file above.")
