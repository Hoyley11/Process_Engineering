import streamlit as st
import pandas as pd
from utils import data_manager
from calculations import hopper_hp, pump_pu

st.set_page_config(page_title="Sizing Engine", layout="wide")
st.title("🧮 Bulk Equipment Sizing Engine")

df_mb = st.session_state.get('mass_balance', pd.DataFrame())
df_equip = data_manager.get_master_list()

if df_mb.empty or df_equip.empty:
    st.warning("Please ensure Mass Balance (Page 1) and Equipment List (Page 2) are loaded.")
    st.stop()

category_map = {
    "Hoppers (HP)": "HP", 
    "Pumps (PU)": "PU", 
    "Thickeners (TH)": "TH",
    "Flotation Cells (FC)": "FC"
}
category = st.selectbox("Select Equipment Category to Size:", list(category_map.keys()))
equip_type_code = category_map[category]
category = st.selectbox("Category", list(category_map.keys()))
type_code = category_map[category]

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

elif equip_type_code == "TH":
    st.subheader("Nuanced Thickener Sizing (Unit-by-Unit)")
    
    df_thickeners = df_equip[df_equip['Type'] == 'TH'].copy()
    
    # We create a column for each thickener tag
    tabs = st.tabs(df_thickeners['Tag'].tolist())
    
    for i, tab in enumerate(tabs):
        with tab:
            tag = df_thickeners.iloc[i]['Tag']
            st.write(f"### Design Parameters for {tag}")
            
            col_in, col_out = st.columns([0.4, 0.6])
            
            with col_in:
                # 1. Map Multiple Streams (Nuance)
                feed_s = st.selectbox(f"Feed Stream ({tag})", df_mb.index, key=f"f_{tag}")
                uflow_s = st.selectbox(f"Underflow Stream ({tag})", df_mb.index, key=f"u_{tag}")
                oflow_s = st.selectbox(f"Overflow Stream ({tag})", df_mb.index, key=f"o_{tag}")
                
                # 2. Design Assumptions
                grind = st.number_input("Design P80 (µm)", value=75, key=f"p80_{tag}")
                flux = st.number_input("Design Flux (t/m²/h)", value=0.5, step=0.05, key=f"flux_{tag}")
                settle = st.number_input("Settling Rate (m/h)", value=3.0, step=0.5, key=f"sr_{tag}")
                round_to = st.selectbox("Round up to nearest (m)", [1.0, 2.5, 5.0, 10.0], key=f"round_{tag}")

            with col_out:
                # 3. Show Case Comparison
                # Pull values from Mass Balance
                s_tph = df_mb.loc[feed_s, 'Solids Mass Flow (t/h)']
                o_m3h = df_mb.loc[oflow_s, 'Slurry (m³/h)']
                
                st.write("**Stream Summary (from SysCAD):**")
                st.table(pd.DataFrame({
                    "Stream": ["Feed", "Underflow", "Overflow"],
                    "Solids (t/h)": [s_tph, df_mb.loc[uflow_s, 'Solids Mass Flow (t/h)'], 0],
                    "Volume (m³/h)": [df_mb.loc[feed_s, 'Slurry (m³/h)'], df_mb.loc[uflow_s, 'Slurry (m³/h)'], o_m3h]
                }))
                
                if st.button(f"Size {tag}", type="primary"):
                    p_data = {'solids_tph': s_tph, 'overflow_m3h': o_m3h}
                    m_inputs = {
                        'design_flux': flux, 'settling_rate': settle, 
                        'round_up_to': round_to, 'p80': grind
                    }
                    res = thickener_tk.calculate(tag, p_data, m_inputs)
                    st.json(res)
                    data_manager.save_equipment_sizing(tag, res)
                    st.success("Sizing Saved.")
