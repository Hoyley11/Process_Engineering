import streamlit as st
import pandas as pd
import math
from utils import data_manager
from calculations import hopper_hp, pump_pu, thickener_th

st.set_page_config(page_title="Sizing Engine", layout="wide")
st.title("🧮 Process Equipment Sizing Engine")

# --- 1. SESSION DATA CHECKS ---
df_mb = st.session_state.get('mass_balance', pd.DataFrame())
df_equip = data_manager.get_master_list()

if df_mb.empty:
    st.warning("⚠️ Please upload a Mass Balance on Page 1 first!")
    st.stop()

if df_equip.empty:
    st.warning("⚠️ Please import an Equipment List on Page 2 first!")
    st.stop()

# --- 2. CATEGORY SELECTION ---
category_map = {
    "Thickeners (TH)": "TH",
    "Pumps (PU)": "PU",
    "Hoppers (HP)": "HP",
    "Flotation Cells (FC)": "FC",
    "Tanks (TK)": "TK"
}
category = st.selectbox("Select Equipment Category to Size:", list(category_map.keys()))
type_code = category_map[category]

# --- 3. FUZZY COLUMN MAPPING ---
col_solids = next((c for c in df_mb.columns if 'solids (t/h)' in str(c).lower()), None)
col_slurry_vol = next((c for c in df_mb.columns if 'slurry' in str(c).lower() and ('m3/h' in str(c).lower() or 'm³/h' in str(c))), None)
col_dens = next((c for c in df_mb.columns if 'density' in str(c).lower() and 't/m3' in str(c).lower()), None)

def get_val(s_num, col_name):
    if not col_name or s_num not in df_mb.index:
        return 0.0
    val = df_mb.loc[s_num, col_name]
    if isinstance(val, pd.Series):
        return float(val.iloc[0])
    return float(val)

st.markdown("---")

# =====================================================================
# THICKENER (TH) MULTI-CASE SIZING
# =====================================================================
if type_code == "TH":
    df_th = df_equip[df_equip['Type'] == 'TH'].copy()
    if df_th.empty:
        st.info("No Thickeners (TH) found.")
        st.stop()

    tabs = st.tabs(df_th['Tag'].tolist())
    for i, tab in enumerate(tabs):
        with tab:
            tag = df_th.iloc[i]['Tag']
            state = data_manager.load_equipment_state(tag) or {}
            
            st.write(f"### {tag} Design Scenarios")
            
            if 'scenarios' not in state:
                default_scenarios = [
                    {"Case": "Nominal", "Factor": 1.0, "Flux": 0.4, "Settling": 3.0},
                    {"Case": "Design (+20%)", "Factor": 1.2, "Flux": 0.4, "Settling": 3.0}
                ]
            else:
                default_scenarios = state['scenarios']

            edited_scenarios = st.data_editor(pd.DataFrame(default_scenarios), num_rows="dynamic", key=f"grid_{tag}")

            col_map, col_results = st.columns([0.4, 0.6])
            with col_map:
                stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
                s_feed = st.selectbox("Feed Stream", stream_options, key=f"f_{tag}")
                f_num = s_feed.split(" | ")[0]
                base_solids = get_val(f_num, col_solids)
                base_vol = get_val(f_num, col_slurry_vol)

            case_results = []
            for _, row in edited_scenarios.iterrows():
                c_solids = base_solids * row['Factor']
                res = thickener_th.calculate(tag, {'solids_tph': c_solids, 'overflow_m3h': base_vol}, 
                                           {'design_flux': row['Flux'], 'settling_rate': row['Settling'], 'round_up_to': 1.0})
                case_results.append({
                    "Case": row['Case'], "Solids (t/h)": round(c_solids, 1), 
                    "Flux": row['Flux'], "Req. Dia (m)": res['critical_dimensions']['Diameter (m)']
                })

            with col_results:
                st.table(pd.DataFrame(case_results))

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            max_calc = max([r['Req. Dia (m)'] for r in case_results]) if case_results else 0.0
            spec_dia = c1.number_input("Specified Diameter (m)", value=float(max_calc), key=f"sp_{tag}")
            
            if st.button(f"✅ Save {tag}", key=f"save_{tag}"):
                final_res = thickener_th.calculate(tag, {'solids_tph': base_solids, 'overflow_m3h': base_vol}, 
                                                {'design_flux': 0.4, 'settling_rate': 3.0, 'round_up_to': 1.0})
                if "critical_dimensions" not in final_res:
                    final_res["critical_dimensions"] = {}
                
                final_res['status'] = "Sized"
                final_res['critical_dimensions']['Diameter (m)'] = float(spec_dia)
                final_res['scenarios'] = edited_scenarios.to_dict('records')
                final_res['mapped_feed'] = s_feed
                
                data_manager.save_equipment_sizing(tag, final_res)
                st.success(f"Final Spec for {tag} saved as {spec_dia}m.")

# =====================================================================
# PUMP (PU) BULK SIZING
# =====================================================================
elif type_code == "PU":
    df_pu = df_equip[df_equip['Type'] == 'PU'].copy()
    grid_data = []
    stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
    
    for _, row in df_pu.iterrows():
        tag = row['Tag']
        state = data_manager.load_equipment_state(tag) or {}
        mi = state.get('manual_inputs', {})
        grid_data.append({
            "Update?": False, "Tag": tag, "Title": row.get('Title', ''),
            "Feed Stream": state.get('mapped_stream_ui', stream_options[0]),
            "TDH (m)": mi.get('tdh_m', 25.0), "Slurry?": mi.get('is_slurry', True)
        })
    
    edited_pu = st.data_editor(pd.DataFrame(grid_data), use_container_width=True, hide_index=True)
    
    if st.button("🚀 Process Pumps"):
        for _, r in edited_pu[edited_pu['Update?']].iterrows():
            s_num = r['Feed Stream'].split(" | ")[0]
            p_data = {'flow_m3h': get_val(s_num, col_slurry_vol), 'density_tm3': get_val(s_num, col_dens)}
            m_in = {'tdh_m': r['TDH (m)'], 'is_slurry': r['Slurry?']}
            res = pump_pu.calculate(r['Tag'], p_data, m_in)
            res['mapped_stream_ui'] = r['Feed Stream']
            res['manual_inputs'] = m_in
            data_manager.save_equipment_sizing(r['Tag'], res)
        st.success("Pumps Updated!")

# =====================================================================
# HOPPER (HP) BULK SIZING
# =====================================================================
elif type_code == "HP":
    df_hp = df_equip[df_equip['Type'] == 'HP'].copy()
    stream_options = [f"{idx} | {row['Stream_Name']}" for idx, row in df_mb.iterrows()]
    grid_data = []
    
    for _, row in df_hp.iterrows():
        tag = row['Tag']
        state = data_manager.load_equipment_state(tag) or {}
        mi = state.get('manual_inputs', {})
        grid_data.append({
            "Update?": False, "Tag": tag,
            "Feed Stream": state.get('mapped_stream_ui', stream_options[0]),
            "Res Time (min)": mi.get('residence_time_min', 1.0),
            "FVF": mi.get('fvf', 1.5)
        })
        
    edited_hp = st.data_editor(pd.DataFrame(grid_data), use_container_width=True, hide_index=True)
    
    if st.button("🚀 Process Hoppers"):
        for _, r in edited_hp[edited_hp['Update?']].iterrows():
            s_num = r['Feed Stream'].split(" | ")[0]
            p_data = {'max_flow_m3h': get_val(s_num, col_slurry_vol)}
            m_in = {'residence_time_min': r['Res Time (min)'], 'fvf': r['FVF'], '
