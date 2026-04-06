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
type_code = category_map[category]

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

if type_code == "TH":
    st.subheader("Unit-by-Unit Multi-Case Thickener Sizing")
    
    df_th = df_equip[df_equip['Type'] == 'TH'].copy()
    tabs = st.tabs(df_th['Tag'].tolist())
    
    for i, tab in enumerate(tabs):
        with tab:
            tag = df_th.iloc[i]['Tag']
            state = data_manager.load_equipment_state(tag) or {}
            
            # --- 1. SETUP SCENARIOS ---
            st.markdown(f"### {tag} Design Scenarios")
            st.info("Define your design cases below (e.g. Nominal, Design +20%, Peak).")
            
            # Initialize scenario data from state or defaults
            if 'scenarios' not in state:
                default_scenarios = [
                    {"Case": "Nominal", "Factor": 1.0, "Flux": 0.4, "Settling": 3.0},
                    {"Case": "Design (+20%)", "Factor": 1.2, "Flux": 0.4, "Settling": 3.0},
                    {"Case": "Worst Case", "Factor": 1.0, "Flux": 0.25, "Settling": 2.0}
                ]
            else:
                default_scenarios = state['scenarios']

            # Editable Scenario Grid
            edited_scenarios = st.data_editor(
                pd.DataFrame(default_scenarios),
                num_rows="dynamic",
                key=f"grid_{tag}",
                use_container_width=True
            )

            # --- 2. STREAM MAPPING ---
            st.markdown("---")
            col_map, col_results = st.columns([0.4, 0.6])
            
            with col_map:
                st.write("**Base Stream Mapping (Nominal)**")
                stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
                s_feed = st.selectbox("Feed Stream", stream_options, key=f"f_{tag}")
                f_num = s_feed.split(" | ")[0]
                
                # Fetch Base Values
                base_solids = float(df_mb.loc[f_num, col_solids].iloc[0] if isinstance(df_mb.loc[f_num, col_solids], pd.Series) else df_mb.loc[f_num, col_solids])
                
            # --- 3. CALCULATE ALL CASES ---
            case_results = []
            for _, row in edited_scenarios.iterrows():
                calc_solids = base_solids * row['Factor']
                # Run the math module for this case
                res = thickener_th.calculate(tag, {'solids_tph': calc_solids}, {'design_flux': row['Flux'], 'settling_rate': row['Settling'], 'round_up_to': 1.0})
                
                case_results.append({
                    "Case": row['Case'],
                    "Solids (t/h)": round(calc_solids, 1),
                    "Flux (t/m2h)": row['Flux'],
                    "Req. Dia (m)": res['critical_dimensions']['Diameter (m)']
                })

            with col_results:
                st.write("**Calculated Requirements**")
                st.table(pd.DataFrame(case_results))

            # --- 4. ENGINEER SPECIFICATION ---
            st.markdown("---")
            st.write("#### Final Engineering Specification")
            c1, c2, c3 = st.columns(3)
            
            # Suggest the maximum calculated diameter as the starting point
            max_calc_dia = max([r['Req. Dia (m)'] for r in case_results])
            
            spec_dia = c1.number_input("Specified Diameter (m)", value=float(max_calc_dia), step=0.5, key=f"spec_{tag}")
            spec_round = c2.selectbox("Round to Standard?", [0, 2.5, 5.0, 10.0], index=1, key=f"rnd_{tag}")
            
            final_dia = spec_dia if spec_round == 0 else (math.ceil(spec_dia / spec_round) * spec_round)
            c3.metric("Final Selection", f"{final_dia} m")

            if st.
