import streamlit as st
import pandas as pd
# Dynamically import your calculation modules
from calculations import hopper_hp, pump_pu 

st.set_page_config(page_title="Sizing Engine", layout="wide")

st.title("🧮 Equipment Sizing Engine")
st.markdown("Select equipment, map process streams, and execute sizing models.")

# 1. Top Section: Equipment Selection
st.subheader("1. Equipment Configuration")
col_tag, col_type = st.columns(2)
with col_tag:
    equip_tag = st.text_input("Equipment Tag", "107780-HP-001")
with col_type:
    # We will eventually auto-detect this, but good for structure now
    equip_type = st.selectbox("Equipment Type", ["Hopper (HP)", "Pump (PU)"])

st.markdown("---")

# 2. Split Screen: Inputs vs Results
col_left, col_right = st.columns([0.35, 0.65])

with col_left:
    st.subheader("2. Process Mapping")
    feed_stream = st.text_input("SysCAD Feed Stream #")
    
    with st.expander("Process Overrides"):
        fvf = st.number_input("Froth Volume Factor", value=1.5)
        
    st.button("Execute Sizing Model", type="primary") # Primary makes it blue/bold

with col_right:
    st.subheader("3. Execution Results")
    
    # Using tabs to organize the heavy output
    tab_summary, tab_mto, tab_sketch = st.tabs(["3-Line Summary", "Material Take-Off", "Geometry Sketch"])
    
    with tab_summary:
        st.info("Awaiting execution...") # Placeholder before they hit the button
    
    with tab_mto:
        st.write("MTO details will appear here.")
        
    with tab_sketch:
        st.write("Matplotlib sketch will render here.")

# 1. Select Equipment to Size
st.subheader("Select Equipment")
equip_tag = st.text_input("Enter Equipment Tag", "107780-HP-001")
equip_type = equip_tag.split('-')[1] # Extracts 'HP'

# 2. Map Streams (Assuming mass balance is loaded in session_state)
st.subheader("Map SysCAD Streams")
if equip_type == "HP":
    feed_stream = st.text_input("Feed Stream Number", "1001")
    res_time = st.number_input("Residence Time (min)", 45)
    
    if st.button("Run Sizing Calculation"):
        # In reality, you fetch this from your uploaded dataframe: df.loc[feed_stream]
        mock_stream_data = {'feed_flow_m3h': 200.3} 
        user_inputs = {'residence_time': res_time}
        
        # Execute the isolated module
        results = hopper_hp.calculate(equip_tag, mock_stream_data, user_inputs)
        
        st.success(f"Successfully sized {equip_tag}!")
        st.write("### 3-Line Description")
        st.text(results["description_3_line"])
        
        st.write("### Material Take Off (MTO)")
        st.json(results["mto"])
        
        if 'mass_balance' not in st.session_state:
    st.warning("Please upload a Mass Balance on Page 1 first!")
    st.stop()

df_mb = st.session_state['mass_balance']

# If user types stream "1001" for the hopper feed:
feed_stream = st.text_input("Feed Stream Number", "1001")

if st.button("Run Sizing"):
    if feed_stream in df_mb.index:
        # Extract the specific row as a dictionary
        stream_data_dict = df_mb.loc[feed_stream].to_dict()
        
        # We need to map SysCAD column names to our calculation variables
        # SysCAD might output "Slurry (m^3/h)", we map it to "feed_flow_m3h"
        mapped_stream_data = {
            'feed_flow_m3h': stream_data_dict.get('Slurry (m^3/h)', 0),
            'solids_sg': stream_data_dict.get('Solids SG', 0),
            # Add other mappings here based on exact SysCAD naming
        }
        
        # Run calculation
        results = hopper_hp.calculate(equip_tag, mapped_stream_data, user_inputs)
        # ... proceed to display and save ...
    else:
        st.error(f"Stream {feed_stream} not found in Mass Balance!")
