import streamlit as st
from pathlib import Path

# =====================================================================
# 1. PAGE CONFIGURATION (Must be the very first Streamlit command)
# =====================================================================
st.set_page_config(
    page_title="Process Calculation Engine",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 2. SYSTEM INITIALIZATION
# =====================================================================
# Ensure our data directories exist when the app boots up
try:
    from utils import data_manager
    data_manager.initialize_master_list()
except ModuleNotFoundError:
    # Failsafe if the utils folder isn't set up yet
    Path("data/states").mkdir(parents=True, exist_ok=True)
    pass

# =====================================================================
# 3. MAIN LANDING PAGE UI
# =====================================================================
st.title("⚙️ Process Engineering Calculation Engine")
st.markdown("---")

# Welcome and Instructions
col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.markdown("""
    ### Welcome to the Calculation Engine
    This application automates equipment sizing, Material Take-Off (MTO) generation, and master list tracking by directly linking standard calculation models to your SysCAD mass balance outputs.

    ### 🚀 How to use this tool:
    Please use the **Sidebar on the left** to navigate through the workflow:

    1. **📊 Mass Balance:** Upload your SysCAD Excel export. The app will automatically parse, clean, and transpose the data into a usable format.
    2. **🧮 Sizing Engine:** Select an equipment tag, map it to a mass balance stream, adjust overrides, and execute the calculation model (e.g., Hoppers, Pumps, Flotation Cells).
    3. **📋 Equipment List:** View the master tracker containing your sized equipment, 3-line descriptions, power summaries, and MTOs. You can download this directly to Excel.
    """)

with col2:
    st.info("""
    **Developer Note:**
    To update or add new sizing calculations, simply drop a new `.py` file into the `/calculations` folder and link it in the Sizing Engine page. 
    The architecture ensures your math remains isolated from the UI layout.
    """)

# =====================================================================
# 4. SIDEBAR GLOBAL ELEMENTS (Shows up on every page)
# =====================================================================
with st.sidebar:
    st.markdown("### Project Status")
    
    # Check if a mass balance is currently loaded in memory
    if 'mass_balance' in st.session_state:
        streams_count = len(st.session_state['mass_balance'])
        st.success(f"✅ Mass Balance Loaded ({streams_count} streams)")
    else:
        st.warning("⚠️ No Mass Balance Loaded")
        
    st.markdown("---")
    st.caption("Powered by Streamlit | Git-Synced")
