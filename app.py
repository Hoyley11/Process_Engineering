import streamlit as st


# Force the app to use the full width of the monitor
st.set_page_config(
    page_title="Process Calc Engine",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Everything inside this block goes into the left panel
with st.sidebar:
    st.image("logo.png") # Great for company branding
    st.markdown("---")
    st.write("**Active Project:** Test Project")
    st.write("**Revision:** Rev A")
  
st.set_page_config(page_title="Process Calculation Engine", layout="wide")

st.title("⚙️ Process Calculation Engine")
st.markdown("""
Welcome to the Process Engineering Calculation Engine. 
Use the sidebar to navigate:
1. **Mass Balance:** Upload and manage SysCAD outputs.
2. **Equipment List:** View master equipment lists and current sizing status.
3. **Sizing Engine:** Map streams to equipment and execute sizing code.
""")
