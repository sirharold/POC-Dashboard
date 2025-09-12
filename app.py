import streamlit as st

# ========================================================================
# CONFIGURACIÓN Y REDIRECCIÓN AUTOMÁTICA
# ========================================================================
# Esta aplicación ahora redirige automáticamente a POC AWS Alive
# Solo esa página es visible, ocultando las páginas de detalles y otras

st.set_page_config(
    page_title="POC AWS Alive", 
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar colapsado por defecto
)

# Redirigir inmediatamente a la página POC AWS Alive
st.switch_page("pages/POC_AWS_Alive.py")