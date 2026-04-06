# pages/2_📋_Equipment_List.py
import streamlit as st
from utils import data_manager

st.title("Equipment Master List")

# Fetch the flat CSV data
df_equipment = data_manager.get_master_list()

if df_equipment.empty:
    st.info("No equipment has been sized yet. Go to the Sizing Engine to get started.")
else:
    # Display as an interactive dataframe
    st.dataframe(
        df_equipment,
        use_container_width=True,
        hide_index=True
    )
    
    # Optional: Add a quick download button for the CSV
    csv = df_equipment.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Equipment List (CSV)",
        data=csv,
        file_name='equipment_list.csv',
        mime='text/csv',
    )
