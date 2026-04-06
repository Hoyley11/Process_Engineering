import streamlit as st
import pandas as pd
from utils import data_manager
from calculations import hopper_hp # Import the math module!

st.set_page_config(page_title="Sizing Engine", layout="wide")
st.title("🧮 Equipment Sizing Engine")

# 1. Fetch data
df_mb = st.session_state.get('mass_balance', pd.DataFrame())
df_equip = data_manager.get_master_list()

if df_mb.empty:
    st.warning("Please upload a Mass Balance on Page 1 first!")
    st.stop()

# 2. Equipment Selection
st.subheader("1. Select Equipment")
# Only show hoppers that need sizing
pending_hoppers = df_equip[(df_equip['Type'] == 'HP')]['Tag'].tolist()

if not pending_hoppers:
    st.info("No hoppers currently pending in the Equipment List.")
    equip_tag = st.text_input("Enter tag manually:", "1000-HP-001")
else:
    equip_tag = st.selectbox("Select pending hopper:", pending_hoppers)

# 3. Process Mapping
col1, col2 = st.columns([0.4, 0.6])

with col1:
    st.subheader("2. Process Variables")
    feed_stream = st.selectbox("Feed Stream from SysCAD:", df_mb.index)
    
    with st.expander("Override Defaults", expanded=True):
        res_time = st.number_input("Residence Time (min)", value=1.0, step=0.1)
        fvf = st.number_input("Froth Volume Factor", value=1.5, step=0.1)
        shape = st.selectbox("Shape", ["Round", "Square"])
        rubber = st.checkbox("Rubber Lined", value=True)

    if st.button("Execute Sizing", type="primary"):
        # Map SysCAD property names to our standard variables
        # *IMPORTANT: Change 'Slurry (m^3/h)' to whatever SysCAD outputs in your file*
        slurry_flow = df_mb.loc[feed_stream, 'Slurry (m^3/h)'] if 'Slurry (m^3/h)' in df_mb.columns else 0.0
        
        stream_data = {'max_flow_m3h': slurry_flow}
        manual_inputs = {
            'residence_time_min': res_time, 'fvf': fvf, 
            'shape': shape, 'rubber_lined': rubber, 'steel_thickness_mm': 10.0
        }
        
        # RUN THE MATH
        results = hopper_hp.calculate(equip_tag, stream_data, manual_inputs)
        
        if "Error" in results.get("status", ""):
            st.error(results["status"])
        else:
            # Store results in memory temporarily so we can display them
            st.session_state['current_results'] = results
            st.success("Sizing complete!")

with col2:
    st.subheader("3. Results")
    if 'current_results' in st.session_state:
        res = st.session_state['current_results']
        st.write("### 3-Line Description")
        st.text(res['description_3_line'])
        
        st.write("### Dimensions & MTO")
        col_dim, col_mto = st.columns(2)
        col_dim.json(res['critical_dimensions'])
        col_mto.json(res['mto'])
        
        if st.button("💾 Save & Commit to Project"):
            data_manager.save_equipment_sizing(equip_tag, res)
            st.success(f"{equip_tag} saved! Equipment list updated.")
