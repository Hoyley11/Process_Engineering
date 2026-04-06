import streamlit as st
import pandas as pd
from utils import data_manager

st.set_page_config(page_title="Equipment List", layout="wide")

st.title("📋 Master Equipment Tracker")
st.markdown("Track the sizing status of all project equipment here.")

# --- 1. UPLOAD BASELINE LIST ---
with st.expander("📥 Import Baseline Equipment List (from Excel)"):
    st.write("Upload your Mechanical Equipment List to populate the tracker. The Excel file must contain 'Tag' and 'Description' columns.")
    uploaded_mel = st.file_uploader("Upload MEL (Excel)", type=['xlsx', 'xls'])
    
    if uploaded_mel:
        try:
            df_mel = pd.read_excel(uploaded_mel)
            
            # Look for the required columns (case-insensitive search)
            col_names = [c.lower() for c in df_mel.columns]
            if 'tag' not in col_names or 'description' not in col_names:
                st.error("Excel file must contain columns named exactly 'Tag' and 'Description'.")
            else:
                # Standardize column names
                tag_col = df_mel.columns[col_names.index('tag')]
                desc_col = df_mel.columns[col_names.index('description')]
                
                # Fetch current master list
                df_master = data_manager.get_master_list()
                existing_tags = df_master['Tag'].tolist() if not df_master.empty else []
                
                new_items_added = 0
                for _, row in df_mel.iterrows():
                    tag = str(row[tag_col]).strip()
                    desc = str(row[desc_col]).strip()
                    
                    if tag != 'nan' and tag not in existing_tags:
                        # Extract the equipment type (e.g., 'HP' from '1000-HP-001')
                        equip_type = tag.split('-')[1] if '-' in tag else "Unknown"
                        
                        new_row = {
                            "Tag": tag,
                            "Type": equip_type,
                            "Status": "Pending Sizing", # Sets it as a to-do item
                            "Description": desc,
                            "Installed Power (kW)": 0.0,
                            "Absorbed Power (kW)": 0.0,
                            "Last Updated": "Not Sized"
                        }
                        df_master = pd.concat([df_master, pd.DataFrame([new_row])], ignore_index=True)
                        new_items_added += 1
                
                # Save the updated master list back to the CSV
                df_master.to_csv(data_manager.MASTER_LIST_PATH, index=False)
                
                if new_items_added > 0:
                    st.success(f"Successfully imported {new_items_added} new equipment tags!")
                    st.rerun() # Refresh the page to show the new table
                else:
                    st.info("No new tags found. All uploaded items already exist in the tracker.")
                    
        except Exception as e:
            st.error(f"Error reading file: {e}")

# --- 2. DISPLAY MASTER TRACKER ---
st.markdown("---")
df_equipment = data_manager.get_master_list()

if df_equipment.empty:
    st.info("No equipment in the tracker yet. Upload a baseline list above to get started.")
else:
    # Quick metrics
    total_equip = len(df_equipment)
    sized_equip = len(df_equipment[df_equipment['Status'] == 'Sized'])
    st.write(f"**Total Equipment:** {total_equip} | **Sized:** {sized_equip} | **Pending:** {total_equip - sized_equip}")
    
    # Color-code the status column using Pandas styling
    def color_status(val):
        color = '#d4edda' if val == 'Sized' else '#fff3cd' if val == 'Pending Sizing' else ''
        return f'background-color: {color}; color: black'

    st.dataframe(
        df_equipment.style.map(color_status, subset=['Status']),
        use_container_width=True,
        hide_index=True
    )
    
    # Download button for the tracker
    csv = df_equipment.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Master Equipment List (CSV)",
        data=csv,
        file_name='Process_Equipment_List.csv',
        mime='text/csv',
    )
