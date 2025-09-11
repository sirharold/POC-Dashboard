"""
VM Detail Page for SAP Infrastructure Dashboard
"""
import streamlit as st
from utils.helpers import (
    load_css,
    get_sample_alarms,
    get_sample_cpu_data,
    get_sample_ram_usage,
    get_sample_disk_data,
    create_alarm_item_html
)

# ========================================================================
# STREAMLIT CONFIGURATION
# ========================================================================

# Use the same page config as the main app for consistency
st.set_page_config(
    page_title="Detalles del Servidor",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def show_vm_details(vm_name: str):
    """
    Display detailed view for a virtual machine.
    
    Args:
        vm_name (str): Name of the virtual machine
    """
    # Ensure vm_name is a string, not a list
    if isinstance(vm_name, list):
        vm_name = vm_name[0]

    st.markdown(f"<h1>Detalles de <span style='color: #00d4ff;'>{vm_name}</span></h1>", unsafe_allow_html=True)
    
    with st.spinner(f"Cargando métricas para {vm_name}..."):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("<h2 style='color: #00d4ff; font-size: 1.5rem;'>🚨 Alarmas Activas</h2>", unsafe_allow_html=True)
            alarms = get_sample_alarms(vm_name)
            for alarm_name, status in alarms:
                st.markdown(create_alarm_item_html(alarm_name, status), unsafe_allow_html=True)
        
        with col2:
            st.selectbox(
                "⏰ Filtro de tiempo",
                ["5 minutos", "15 minutos", "30 minutos", "1 hora", "3 horas", "6 horas", "12 horas"],
                index=3,
                key="time_filter"
            )
            
            st.markdown("<h2 style='color: #00d4ff; font-size: 1.5rem;'>📊 Métricas de Rendimiento</h2>", unsafe_allow_html=True)
            
            metric_col1, metric_col2 = st.columns(2)
            
            with metric_col1:
                st.markdown("<span style='color: white; font-weight: 600;'>🖥️ CPU Usage</span>", unsafe_allow_html=True)
                cpu_data = get_sample_cpu_data()
                for i, cpu_usage in enumerate(cpu_data):
                    st.progress(cpu_usage/100, f"CPU {i+1}: {cpu_usage}%")
                
                st.markdown("<span style='color: white; font-weight: 600;'>💾 RAM Usage</span>", unsafe_allow_html=True)
                ram_usage = get_sample_ram_usage()
                st.progress(ram_usage/100, f"RAM: {ram_usage}% de 32GB")
            
            with metric_col2:
                st.markdown("<span style='color: white; font-weight: 600;'>💿 Disk Usage</span>", unsafe_allow_html=True)
                disk_data = get_sample_disk_data()
                for disk_name, usage, capacity in disk_data:
                    st.progress(usage/100, f"{disk_name} {usage}% de {capacity}")

# ========================================================================
# MAIN APPLICATION LOGIC
# ========================================================================

load_css()

# Add a button to go back to the main dashboard
st.page_link("pages/1_Production.py", label="← Volver al Dashboard", icon="🏠")

if 'selected_vm' in st.session_state and st.session_state.selected_vm:
    show_vm_details(st.session_state.selected_vm)
else:
    st.markdown("<h1>Seleccione un servidor</h1>", unsafe_allow_html=True)
    st.info("Por favor, regrese al Dashboard Principal y haga clic en una tarjeta de servidor para ver sus detalles.")