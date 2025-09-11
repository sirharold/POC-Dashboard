"""
SAP Infrastructure Dashboard - QA Environment
"""

import streamlit as st
from utils.helpers import load_css, load_config, create_env_switcher_header
from components.group_container import create_group_from_config

# ========================================================================
# STREAMLIT CONFIGURATION
# ========================================================================

st.set_page_config(
    page_title="QA - Dashboard EPMAPS",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========================================================================
# SESSION STATE INITIALIZATION
# ========================================================================

if 'selected_vm' not in st.session_state:
    st.session_state.selected_vm = None

def main_dashboard():
    """
    Display the main dashboard with all server groups.
    """
    # Page title with environment switcher
    create_env_switcher_header("QA")
    
    config = load_config()
    if not config:
        st.error("No se pudo cargar la configuración. Verifique el archivo `config.yaml`.")
        return

    server_groups = config.get("server_groups", [])
    
    # Create groups in a 2-column layout for optimal space usage
    for i in range(0, len(server_groups), 2):
        col1, col2 = st.columns(2)
        
        with col1:
            if i < len(server_groups):
                create_group_from_config(server_groups[i], "qa")
        
        with col2:
            if i + 1 < len(server_groups):
                create_group_from_config(server_groups[i + 1], "qa")

# ========================================================================
# MAIN APPLICATION LOGIC
# ========================================================================

def main():
    load_css()

    # Check for query params for navigation
    query_params = st.query_params
    if "selected_vm" in query_params:
        st.session_state.selected_vm = query_params.get("selected_vm")
        st.switch_page("pages/_1_Detalles_del_Servidor.py")
    
    main_dashboard()

if __name__ == "__main__":
    main()