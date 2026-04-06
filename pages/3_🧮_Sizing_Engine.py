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
category_map = {
    "Hoppers (HP)": "HP", 
    "Pumps (PU)": "PU", 
    "Flotation Cells (FL)": "FL"
}
category = st.selectbox("Category", list(category_map.keys()))
equip_type_code = category_map[category]

st.markdown("---")

# =====================================================================
# HOPPER BULK SIZING LOGIC
# =====================================================================
if equip_type_code == "HP":
    st.subheader("2. Bulk Hopper Process Mapping")
    
    # 1. Filter the master list for Hoppers
    df_hoppers = df_equip[df_equip['Type'] == 'HP'].copy()
    if df_hoppers.empty:
        st.info("No hoppers found in the current Equipment List.")
        st.stop()
        
    # 2. Global Stream Property Selection
    # (Select the Flow column once for all hoppers to save grid space)
    likely_flow_cols = [c for c in df_mb.columns if 'slurry' in str(c).lower() and ('m3' in str(c).lower() or 'm^3' in str(c).lower())]
    default_flow_idx = df_mb.columns.tolist().index(likely_flow_cols[0]) if likely_flow_cols else 0
    flow_col_global = st.selectbox("Global 'Slurry Flow' Property:", df_mb.columns, index=default_flow_idx)
    
    # 3. Build the Editable Grid Data
    stream_options = df_mb.index.tolist()
    grid_data = []
    
    for _, row in df_hoppers.iterrows():
        tag = row['Tag']
        
        # Load previous sizing state if it exists to prepopulate the grid!
        existing_state = data_manager.load_equipment_state(tag)
        
        # Defaults
        feed_stream = stream_options[0] if stream_options else ""
        res_time = 1.0
        fvf = 1.5
        shape = "Round"
        rubber = True
        
        # Override defaults if previously saved
        if existing_state and 'manual_inputs' in existing_state:
            prev_stream = existing_state.get('mapped_stream', "")
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
    
    # 4. Render the Interactive Grid
    st.write("Edit process parameters directly in the grid below:")
    
    edited_df = st.data_editor(
        df_grid,
        column_config={
            "Tag": st.column_config.TextColumn("Tag", disabled=True),
            "Title/Desc": st.column_config.TextColumn("Title/Desc", disabled=True),
            "Feed Stream": st.column_config.SelectboxColumn("Feed Stream", options=stream_options, required=True),
            "Res Time (min)": st.column_config.NumberColumn("Res Time (min)", min_value=0.1, step=0.5, format="%.2f"),
            "FVF": st.column_config.NumberColumn("FVF", min_value=1.0, step=0.1, format="%.2f"),
            "Shape": st.column_config.SelectboxColumn("Shape", options=["Round", "Square"], required=True),
            "Rubber Lined": st.column_config.CheckboxColumn("Rubber Lined")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # 5. Execute Bulk Sizing
    if st.button("🚀 Execute & Save Bulk Sizing", type="primary"):
        success_count = 0
        results_list = []
        
        with st.spinner("Calculating MTOs and sizing all hoppers..."):
            for _, row in edited_df.iterrows():
                tag = row['Tag']
                stream = row['Feed Stream']
                
                # Fetch exact flow from mass balance
                try:
                    slurry_flow = float(df_mb.loc[stream, flow_col_global])
                except KeyError:
                    slurry_flow = 0.0
                    
                stream_data = {'max_flow_m3h': slurry_flow}
                manual_inputs = {
                    'residence_time_min': row['Res Time (min)'],
                    'fvf': row['FVF'],
                    'shape': row['Shape'],
                    'rubber_lined': row['Rubber Lined'],
                    'steel_thickness_mm': 10.0 # Could expose this to the grid later if needed
                }
                
                # Run isolated math module
                res = hopper_hp.calculate(tag, stream_data, manual_inputs)
                
                # Inject UI choices into the result so we can load them next time
                res['mapped_stream'] = stream
                res['manual_inputs'] = manual_inputs
                
                # Save to Data Manager
                data_manager.save_equipment_sizing(tag, res)
                results_list.append(res)
                success_count += 1
        
        st.success(f"Successfully sized and saved {success_count} hoppers!")
        
        # 6. Show Summary Results Matrix
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

# =====================================================================
# PUMP / OTHER EQUIPMENT PLACEHOLDERS
# =====================================================================
elif equip_type_code == "PU":
    st.info("🚧 Pump bulk sizing module under development...")
    # This is where we will add the pump logic next!
elif equip_type_code == "FL":
    st.info("🚧 Flotation bulk sizing module under development...")
