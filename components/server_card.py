"""
Server Card Component for SAP Infrastructure Dashboard
"""
import streamlit as st
from utils.helpers import (
    get_vm_status, get_vm_alerts, calculate_availability, create_server_card_html
)


def create_server_card(vm_name: str, environment: str):
    """
    Create a server card component.
    
    Args:
        vm_name (str): Name of the virtual machine
        environment (str): The current environment ('prod', 'qa', 'dev').
    """
    status = get_vm_status(vm_name, environment)
    alerts_data = get_vm_alerts(vm_name)
    availability = calculate_availability(status)
    
    # Display the server card HTML which now includes the alert bar
    st.markdown(
        create_server_card_html(vm_name, status, availability, alerts_data), 
        unsafe_allow_html=True
    )