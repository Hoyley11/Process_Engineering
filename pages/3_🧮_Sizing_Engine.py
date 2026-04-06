import streamlit as st
import pandas as pd
from utils import data_manager
from calculations import hopper_hp, pump_pu, thickener_th # Renamed to TH

st.set_page_config(page_title="Sizing Engine", layout="wide")
st.title("🧮 Bulk Equipment Sizing Engine")

# --- 1. FETCH SYSTEM DATA ---
df_mb = st.session_state.get('mass_balance', pd.DataFrame())
df_equip = data_manager.get_master_list()

if df_mb.empty or df_equip.empty:
    st.warning("⚠️ Please ensure Mass Balance and Equipment List are loaded.")
    st.stop()

# --- 2. UPDATED CATEGORY MAPPING ---
category_map = {
    "Thickeners (TH)": "TH",
    "Flotation Cells (FC)": "FC",
    "Tanks (TK)": "TK",
    "Filters (FL)": "FL",
    "Mills (ML)": "ML",
    "Crushers (CR)": "CR",
    "Conveyors (CV)": "CV",
    "Hoppers (HP)": "HP",
    "Pumps (PU)": "PU"
}
category = st.selectbox("Select Equipment Category to Size:", list(category_map.keys()))
equip_type_code = category_map[category]

st.markdown("---")

if type_code == "PU":
    st.subheader("Bulk Pump Mapping & Sizing")
    df_pumps = df_equip[df_equip['Type'] == 'PU'].copy()
    
    col_flow = next((c for c in df_mb.columns if 'Slurry (m³/h)' in str(c)), None)
    col_dens = next((c for c in df_mb.columns if 'Slurry Density (t/m3)' in str(c)), None)
    
    stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
    
    grid_data = []
    for _, row in df_pumps.iterrows():
        tag = row['Tag']
        title = (row.get('Title', '') or "").lower()
        
        # --- FIX: SAFE STATE LOADING ---
        state = data_manager.load_equipment_state(tag) or {} 
        mi = state.get('manual_inputs', {})
        
        # Defaults + Keyword Detection
        d_type = "Horizontal"
        if "sump" in title: d_type = "Sump"
        
        d_sub = "Centrifugal"
        if "dosing" in title: d_sub = "Dosing"
        elif "hose" in title: d_sub = "Hose"
        elif "aodd" in title: d_sub = "AODD"
        
        grid_data.append({
            "Update?": False,
            "Tag": tag,
            "Title": row.get('Title', ''),
            "Feed Stream": state.get('mapped_stream_ui', stream_options[0]),
            "TDH (m)": mi.get('tdh_m', 25.0),
            "Pump Type": mi.get('pump_type', d_type),
            "Sub-Type": mi.get('sub_type', d_sub),
            "Slurry?": mi.get('is_slurry', True)
        })

    edited_pumps = st.data_editor(
        pd.DataFrame(grid_data),
        column_config={
            "Tag": st.column_config.TextColumn("Tag", disabled=True),
            "Feed Stream": st.column_config.SelectboxColumn("Feed Stream", options=stream_options),
            "Pump Type": st.column_config.SelectboxColumn("Pump Type", options=["Horizontal", "Sump", "Vertical"]),
            "Sub-Type": st.column_config.SelectboxColumn("Sub-Type", options=["Centrifugal", "Dosing", "Hose", "AODD", "Cyclone Feed"]),
            "TDH (m)": st.column_config.NumberColumn("TDH (m)", step=1.0)
        },
        hide_index=True, use_container_width=True
    )

    if st.button("🚀 Execute Pump Sizing"):
        to_up = edited_pumps[edited_pumps['Update?'] == True]
        for _, r in to_up.iterrows():
            s_num = r['Feed Stream'].split(" | ")[0]
            p_data = {
                'flow_m3h': df_mb.loc[s_num, col_flow],
                'density_tm3': df_mb.loc[s_num, col_dens]
            }
            m_in = {
                'tdh_m': r['TDH (m)'], 'pump_type': r['Pump Type'],
                'sub_type': r['Sub-Type'], 'is_slurry': r['Slurry?']
            }
            res = pump_pu.calculate(r['Tag'], p_data, m_in)
            res['mapped_stream_ui'] = r['Feed Stream']
            res['manual_inputs'] = m_in
            data_manager.save_equipment_sizing(r['Tag'], res)
        st.success("Calculations complete!")
        st.rerun()

# =====================================================================
# THICKENER (TH) NUANCED SIZING
# =====================================================================
if equip_type_code == "TH":
    st.subheader("Unit-by-Unit Thickener Sizing")
    
    df_th = df_equip[df_equip['Type'] == 'TH'].copy()
    if df_th.empty:
        st.info("No Thickeners (TH) found in Equipment List.")
        st.stop()

    # Define the property keys for the math
    col_solids = next((c for c in df_mb.columns if 'Solids Mass Flow (t/h)' in str(c)), None)
    col_slurry_vol = next((c for c in df_mb.columns if 'Slurry (m³/h)' in str(c)), None)

    # Create Tabs for each Thickener
    tabs = st.tabs(df_th['Tag'].tolist())
    
    for i, tab in enumerate(tabs):
        with tab:
            tag = df_th.iloc[i]['Tag']
            title = df_th.iloc[i].get('Title', 'Untitled Thickener')
            st.markdown(f"### {tag}: {title}")
            
            # Load Previous State
            state = data_manager.load_equipment_state(tag) or {}
            mi = state.get('manual_inputs', {})

            col_ui, col_stats = st.columns([0.4, 0.6])
            
            with col_ui:
                st.write("**Stream Mapping**")
                stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
                
                s_feed = st.selectbox("Feed Stream", stream_options, key=f"f_{tag}", index=stream_options.index(state.get('mapped_feed', stream_options[0])) if state.get('mapped_feed') in stream_options else 0)
                s_oflow = st.selectbox("Overflow Stream", stream_options, key=f"o_{tag}", index=stream_options.index(state.get('mapped_oflow', stream_options[0])) if state.get('mapped_oflow') in stream_options else 0)
                s_uflow = st.selectbox("Underflow Stream", stream_options, key=f"u_{tag}", index=stream_options.index(state.get('mapped_uflow', stream_options[0])) if state.get('mapped_uflow') in stream_options else 0)

                st.markdown("---")
                st.write("**Design Assumptions**")
                flux = st.number_input("Design Flux (t/m²/h)", value=mi.get('design_flux', 0.4), step=0.05, key=f"flux_{tag}")
                settle = st.number_input("Settling Rate (m/h)", value=mi.get('settling_rate', 3.0), step=0.1, key=f"sr_{tag}")
                round_val = st.selectbox("Round up to nearest (m)", [1.0, 2.5, 5.0], index=1, key=f"rd_{tag}")

            with col_stats:
                st.write("**Mass Balance Verification**")
                # Extract numbers for display
                f_num = s_feed.split(" | ")[0]
                o_num = s_oflow.split(" | ")[0]
                u_num = s_uflow.split(" | ")[0]
                
                summary_df = pd.DataFrame({
                    "Property": ["Solids (t/h)", "Volume (m³/h)"],
                    "Feed": [df_mb.loc[f_num, col_solids], df_mb.loc[f_num, col_slurry_vol]],
                    "Overflow": [df_mb.loc[o_num, col_solids], df_mb.loc[o_num, col_slurry_vol]],
                    "Underflow": [df_mb.loc[u_num, col_solids], df_mb.loc[u_num, col_slurry_vol]]
                })
                st.table(summary_df)

                if st.button(f"🚀 Size and Save {tag}", key=f"btn_{tag}"):
                    p_data = {
                        'solids_tph': df_mb.loc[f_num, col_solids],
                        'overflow_m3h': df_mb.loc[o_num, col_slurry_vol]
                    }
                    m_in = {
                        'design_flux': flux, 'settling_rate': settle, 
                        'round_up_to': round_val
                    }
                    # Run Math
                    from calculations import thickener_th
                    res = thickener_th.calculate(tag, p_data, m_in)
                    
                    # Add UI context for persistence
                    res['mapped_feed'] = s_feed
                    res['mapped_oflow'] = s_oflow
                    res['mapped_uflow'] = s_uflow
                    res['manual_inputs'] = m_in
                    
                    data_manager.save_equipment_sizing(tag, res)
                    st.success(f"Sizing for {tag} committed to project.")
                    st.json(res['critical_dimensions'])
