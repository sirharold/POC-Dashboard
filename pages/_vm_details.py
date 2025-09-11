"""
VM Details Page for SAP Infrastructure Dashboard
"""
import streamlit as st
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import (
    load_css, get_sample_alarms, get_sample_cpu_data, 
    get_sample_disk_data, get_sample_ram_usage,
    create_alarm_item_html
)

def show_vm_details(vm_name: str):
    """
    Display detailed view for a specific virtual machine.
    
    Args:
        vm_name (str): Name of the virtual machine
    """
    # Load CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    
    # Page title
    st.markdown(f"<h1>Detalles de {vm_name}</h1>", unsafe_allow_html=True)
    
    # Create two columns layout
    col1, col2 = st.columns([1, 2])
    
    # Left column: Alarms
    with col1:
        st.markdown(
            "<h2 style='color: #00d4ff; font-size: 1.5rem;'>🚨 Alarmas Activas</h2>", 
            unsafe_allow_html=True
        )
        
        alarms = get_sample_alarms(vm_name)
        
        for alarm_name, status in alarms:
            st.markdown(
                create_alarm_item_html(alarm_name, status), 
                unsafe_allow_html=True
            )
    
    # Right column: Metrics and filters
    with col2:
        # Time filter
        time_filter = st.selectbox(
            "⏰ Filtro de tiempo",
            ["5 minutos", "15 minutos", "30 minutos", "1 hora", "3 horas", "6 horas", "12 horas"],
            index=3
        )
        
        st.markdown(
            "<h2 style='color: #00d4ff; font-size: 1.5rem;'>📊 Métricas de Rendimiento</h2>", 
            unsafe_allow_html=True
        )
        
        # Performance metrics in two columns
        metric_col1, metric_col2 = st.columns(2)
        
        with metric_col1:
            # CPU Usage
            st.markdown(
                "<span style='color: white; font-weight: 600;'>🖥️ CPU Usage</span>", 
                unsafe_allow_html=True
            )
            
            cpu_data = get_sample_cpu_data(cores=4)
            for i, cpu_usage in enumerate(cpu_data):
                st.progress(cpu_usage/100, f"CPU {i+1}: {cpu_usage}%")
            
            # RAM Usage
            st.markdown(
                "<span style='color: white; font-weight: 600;'>💾 RAM Usage</span>", 
                unsafe_allow_html=True
            )
            ram_usage = get_sample_ram_usage()
            st.progress(ram_usage/100, f"RAM: {ram_usage}% de 32GB")
        
        with metric_col2:
            # Disk Usage
            st.markdown(
                "<span style='color: white; font-weight: 600;'>💿 Disk Usage</span>", 
                unsafe_allow_html=True
            )
            
            disks = get_sample_disk_data()
            for disk_name, usage, capacity in disks:
                st.progress(usage/100, f"{disk_name} {usage}% de {capacity}")
    
    # Back button
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← VOLVER AL DASHBOARD", key="back_btn", help="Regresar al dashboard principal"):
            st.session_state.selected_vm = None
            st.rerun()

def main():
    """
    Main function for the VM details page.
    """
    st.set_page_config(
        page_title="VM Details - Dashboard POC",
        page_icon="🖥️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Get VM name from session state or query params
    vm_name = st.session_state.get('selected_vm', 'Unknown VM')
    
    if vm_name == 'Unknown VM':
        st.error("No VM selected. Please return to the main dashboard.")
        if st.button("Go to Dashboard"):
            st.switch_page("app.py")
    else:
        show_vm_details(vm_name)

if __name__ == "__main__":
    main()