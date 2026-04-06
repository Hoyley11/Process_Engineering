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

# --- 2. CATEGORY SELECTION ---
category_map = {"Hoppers (HP)": "HP", "Pumps (PU)": "PU", "Flotation Cells (FL)": "FL"}
category = st.selectbox("Select Equipment Category to Size:", list(category_map.keys()))
equip_type_code = category_map[category]

st.markdown("---")

if equip_type_code == "HP":
    st.subheader("Bulk Hopper Process Mapping")
    
    df_hoppers = df_equip[df_equip['Type'] == 'HP'].copy()
    if df_hoppers.empty:
        st.info("No hoppers found in the Equipment List.")
        st.stop()
        
    # --- FIXED: EXACT PROPERTY MATCHING ---
    # Hunting specifically for 'Slurry (m³/h)'
    slurry_col = next((col for col in df_mb.columns if 'Slurry (m³/h)' in str(col)), None)
    
    # Failsafe: if the superscript version isn't found, look for standard m3/h
    if not slurry_col:
        slurry_col = next((col for col in df_mb.columns if 'slurry' in str(col).lower() and 'm3/h' in str(col).lower()), None)

    if not slurry_col:
        st.error("Could not find property 'Slurry (m³/h)' in Mass Balance. Please check headers.")
        st.stop()
    else:
        st.success(f"✅ Linked to Mass Balance Property: **{slurry_col}**")

    # Unified Searchable Stream Options
    stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
    
    # --- 3. BUILD GRID WITH PERSISTENT STATE ---
    grid_data = []
    for _, row in df_hoppers.iterrows():
        tag = row['Tag']
        
        # PERSISTENCE CHECK: Load previously saved data for this tag
        existing_state = data_manager.load_equipment_state(tag)
        
        # Default values
        feed_stream = stream_options[0] if stream_options else ""
        res_time = 1.0
        fvf = 1.5
        shape = "Round"
        rubber = True
        
        # If we have a saved state, use those values instead of defaults
        if existing_state and 'mapped_stream_ui' in existing_state:
            prev_stream = existing_state.get('mapped_stream_ui', "")
            if prev_stream in stream_options:
                feed_stream = prev_stream
            
            # Pull saved manual inputs
            mi = existing_state.get('manual_inputs', {})
            res_time = mi.get('residence_time_min', res_time)
            fvf = mi.get('fvf', fvf)
            shape = mi.get('shape', shape)
            rubber = mi.get('rubber_lined', rubber)
            
        grid_data.append({
            "Update?": False, # NEW: Update Flag
            "Tag": tag,
            "Title/Desc": row.get('Title', '') or row.get('Description', ''),
            "Feed Stream": feed_stream,
            "Res Time (min)": float(res_time),
            "FVF": float(fvf),
            "Shape": shape,
            "Rubber Lined": rubber
        })
        
    df_grid = pd.DataFrame(grid_data)
    
    st.info("💡 **Tip:** Check the 'Update?' box for specific items you want to calculate/re-calculate.")
    
    # --- 4. RENDER DATA EDITOR ---
    edited_df = st.data_editor(
        df_grid,
        column_config={
            "Update?": st.column_config.CheckboxColumn("Update?", help="Only checked items will be processed"),
            "Tag": st.column_config.TextColumn("Tag", disabled=True),
            "Title/Desc": st.column_config.TextColumn("Title/Desc", disabled=True),
            "Feed Stream": st.column_config.SelectboxColumn("Feed Stream", options=stream_options, required=True),
            "Res Time (min)": st.column_config.NumberColumn("Res Time (min)", min_value=0.1, step=0.1, format="%.1f"),
            "FVF": st.column_config.NumberColumn("FVF", min_value=1.0, step=0.1, format="%.1f"),
            "Shape": st.column_config.SelectboxColumn("Shape", options=["Round", "Square"], required=True)
        },
        hide_index=True,
        use_container_width=True
    )
    
    # --- 5. EXECUTION (ONLY FOR CHECKED ROWS) ---
    if st.button("🚀 Process Selected Updates", type="primary"):
        # Filter for rows where Update? is True
        to_update = edited_df[edited_df['Update?'] == True]
        
        if to_update.empty:
            st.warning("Please check at least one 'Update?' box.")
        else:
            success_count = 0
            with st.spinner(f"Processing {len(to_update)} equipment updates..."):
                for _, row in to_update.iterrows():
                    tag = row['Tag']
                    ui_stream_selection = row['Feed Stream']
                    stream_number = ui_stream_selection.split(" | ")[0]
                    
                    try:
                        slurry_flow = float(df_mb.loc[stream_number, slurry_col])
                    except Exception:
                        slurry_flow = 0.0
                        
                    stream_data = {'max_flow_m3h': slurry_flow}
                    manual_inputs = {
                        'residence_time_min': row['Res Time (min)'],
                        'fvf': row['FVF'],
                        'shape': row['Shape'],
                        'rubber_lined': row['Rubber Lined'],
                        'steel_thickness_mm': 10.0
                    }
                    
                    # Execute Math
                    res = hopper_hp.calculate(tag, stream_data, manual_inputs)
                    
                    # Store UI context for future page loads
                    res['mapped_stream_number'] = stream_number
                    res['mapped_stream_ui'] = ui_stream_selection
                    res['manual_inputs'] = manual_inputs
                    
                    # Save Persistent State
                    data_manager.save_equipment_sizing(tag, res)
                    success_count += 1
            
            st.success(f"Successfully updated and committed {success_count} equipment items.")
            st.rerun() # Refresh to clear checkmarks and show updated data

elif equip_type_code == "PU":
    st.info("🚧 Pump bulk sizing module under development...")
