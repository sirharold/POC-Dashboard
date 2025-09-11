"""
Group Container Component for SAP Infrastructure Dashboard
"""
import streamlit as st
from utils.helpers import create_group_container_html
from components.server_card import create_server_card


def create_group_from_config(group_config: dict, environment: str):
    """
    Create a group of servers from a configuration dictionary.
    
    Args:
        group_config (dict): Dictionary containing group name, servers, and css_class.
        environment (str): The current environment ('prod', 'qa', 'dev').
    """
    # Display group header
    st.markdown(
        create_group_container_html(group_config['name'], group_config['css_class']), 
        unsafe_allow_html=True
    )
    
    # Arrange servers in columns based on count
    servers = group_config['servers']
    num_servers = len(servers)
    if num_servers <= 3:
        cols = st.columns(3)
        for idx, server in enumerate(servers):
            with cols[idx]:
                create_server_card(server, environment)
    elif num_servers <= 6:
        cols = st.columns(6)
        for idx, server in enumerate(servers):
            with cols[idx]:
                create_server_card(server, environment)
    else:
        # For more than 6 servers, create multiple rows
        for i in range(0, num_servers, 6):
            cols = st.columns(6)
            for j, server in enumerate(servers[i:i+6]):
                with cols[j]:
                    create_server_card(server, environment)