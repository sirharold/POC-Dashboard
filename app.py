import streamlit as st

# ========================================================================
# CUSTOM SIDEBAR NAVIGATION
# ========================================================================
# By manually building the sidebar, we gain full control over which pages
# are displayed, bypassing the anomalous behavior of the default auto-generated
# sidebar.

st.set_page_config(
    page_title="Dashboard EPMAPS",
    page_icon="🏠",
    layout="wide"
)

# --- Custom Sidebar --- 
st.sidebar.title("Navegación Principal")
st.sidebar.page_link("pages/1_Production.py", label="Producción", icon="🚀")
st.sidebar.page_link("pages/2_QA.py", label="QA", icon="🧪")
st.sidebar.page_link("pages/3_DEV.py", label="DEV", icon="🛠️")
st.sidebar.page_link("pages/4_POC.py", label="POC - AWS Live", icon="☁️")

# --- Main Page Content ---
st.title("Bienvenido al Dashboard de Monitoreo EPMAPS")
st.info("Por favor, selecciona un ambiente de la barra de navegación lateral para comenzar.")

st.divider()

st.header("Acerca de esta Aplicación")
st.write("""
Esta aplicación proporciona una vista centralizada del estado y rendimiento de la infraestructura crítica de EPMAPS.
- **Ambientes (Prod, QA, DEV):** Muestran una vista general de los servidores en cada entorno (actualmente con datos de maqueta).
- **POC - AWS Live:** Es una prueba de concepto que se conecta en tiempo real a AWS para mostrar el estado de las instancias y sus alarmas.
""")