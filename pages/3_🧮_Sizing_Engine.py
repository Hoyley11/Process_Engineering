import streamlit as st
import pandas as pd
from utils import data_manager
from calculations import hopper_hp

st.set_page_config(page_title="Sizing Engine", layout="wide")
st.title("🧮 Bulk Equipment Sizing Engine")

# --- 1. FETCH SYSTEM DATA ---
df_mb = st.session_state.get('mass_balance', pd.DataFrame())
df_equip = data_manager.get_master_list()

if df_mb.empty:
    st.warning("⚠️ Please upload a Mass Balance on Page 1 first!")
    st.stop()

if df_equip.empty:
    st.warning("⚠️ Please import an Equipment List on Page 2 first!")
    st.stop()

# --- 2. EQUIPMENT CATEGORY SELECTION ---
st.subheader("1. Select Equipment Category")
category_map = {"Hoppers (HP)": "HP", "Pumps (PU)": "PU", "Flotation Cells (FL)": "FL"}
category = st.selectbox("Category", list(category_map.keys()))
equip_type_code = category_map[category]

st.markdown("---")

# =====================================================================
# HOPPER BULK SIZING LOGIC
# =====================================================================
if equip_type_code == "HP":
    st.subheader("2. Bulk Hopper Process Mapping")
    
    df_hoppers = df_equip[df_equip['Type'] == 'HP'].copy()
    if df_hoppers.empty:
        st.info("No hoppers found in the current Equipment List.")
        st.stop()
        
    # Programmatically find the Slurry m3/h column
    slurry_col = next((col for col in df_mb.columns if 'slurry' in str(col).lower() and ('m3/h' in str(col).lower() or 'm^3/h' in str(col).lower())), None)
    
    if not slurry_col:
        st.error("Could not find a property matching 'Slurry (m^3/h)' in the Mass Balance.")
        st.stop()
    else:
        st.success(f"✅ Flow Property Locked: **{slurry_col}**")

    # Build the Searchable Dropdown Options (Combines No. and Name for easy searching)
    stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
    
    # Build Grid Data
    grid_data = []
    for _, row in df_hoppers.iterrows():
        tag = row['Tag']
        existing_state = data_manager.load_equipment_state(tag)
        
        feed_stream = stream_options[0] if stream_options else ""
        res_time = 1.0
        fvf = 1.5
        shape = "Round"
        rubber = True
        
        if existing_state and 'manual_inputs' in existing_state:
            prev_stream = existing_state.get('mapped_stream_ui', "")
            if prev_stream in stream_options:
                feed_stream = prev_stream
                
            mi = existing_state['manual_inputs']
            res_time = mi.get('residence_time_min', res_time)
            fvf = mi.get('fvf', fvf)
            shape = mi.get('shape', shape)
            rubber = mi.get('rubber_lined', rubber)
            
        grid_data.append({
            "Tag": tag,
            "Title/Desc": row.get('Title', '') or row.get('Description', ''),
            "Feed Stream": feed_stream,
            "Res Time (min)": float(res_time),
            "FVF": float(fvf),
            "Shape": shape,
            "Rubber Lined": rubber
        })
        
    df_grid = pd.DataFrame(grid_data)
    
    st.write("Edit process parameters directly in the grid below. **Tip: Click the Feed Stream cell and type a name or number to search.**")
    
    edited_df = st.data_editor(
        df_grid,
        column_config={
            "Tag": st.column_config.TextColumn("Tag", disabled=True),
            "Title/Desc": st.column_config.TextColumn("Title/Desc", disabled=True),
            "Feed Stream": st.column_config.SelectboxColumn("Feed Stream", options=stream_options, required=True),
            "Res Time (min)": st.column_config.NumberColumn("Res Time (min)", min_value=0.1, step=0.5, format="%.2f"),
            "FVF": st.column_config.NumberColumn("FVF", min_value=1.0, step=0.1, format="%.2f"),
            "Shape": st.column_config.SelectboxColumn("Shape", options=["Round", "Square"], required=True)
        },
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("🚀 Execute & Save Bulk Sizing", type="primary"):
        success_count = 0
        results_list = []
        
        with st.spinner("Calculating MTOs and sizing all hoppers..."):
            for _, row in edited_df.iterrows():
                tag = row['Tag']
                ui_stream_selection = row['Feed Stream']
                
                # Split the UI selection back into just the Stream Number for the data lookup
                stream_number = ui_stream_selection.split(" | ")[0]
                
                try:
                    slurry_flow = float(df_mb.loc[stream_number, slurry_col])
                except KeyError:
                    slurry_flow = 0.0
                    
                stream_data = {'max_flow_m3h': slurry_flow}
                manual_inputs = {
                    'residence_time_min': row['Res Time (min)'],
                    'fvf': row['FVF'],
                    'shape': row['Shape'],
                    'rubber_lined': row['Rubber Lined'],
                    'steel_thickness_mm': 10.0
                }
                
                res = hopper_hp.calculate(tag, stream_data, manual_inputs)
                
                res['mapped_stream_number'] = stream_number
                res['mapped_stream_ui'] = ui_stream_selection # Save for the grid prepopulation
                res['manual_inputs'] = manual_inputs
                
                data_manager.save_equipment_sizing(tag, res)
                results_list.append(res)
                success_count += 1
        
        st.success(f"Successfully sized and saved {success_count} hoppers!")
        
        st.subheader("3. Sizing Results Summary")
        summary_data = []
        for r in results_list:
            if "Error" not in r.get("status", ""):
                summary_data.append({
                    "Tag": r['tag'],
                    "Dia/Width (mm)": r['critical_dimensions']['Diameter/Width (mm)'],
                    "Height (mm)": r['critical_dimensions']['Total Height (mm)'],
                    "Carbon Steel (kg)": r['mto']['Carbon Steel (kg)'],
                    "Rubber Lining (m2)": r['mto']['Rubber Lining (m2)']
                })
            else:
                summary_data.append({"Tag": r['tag'], "Dia/Width (mm)": "Error"})
                
        st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)

elif equip_type_code == "PU":
    st.info("🚧 Pump bulk sizing module under development...")
elif equip_type_code == "FL":
    st.info("🚧 Flotation bulk sizing module under development...")
