
"""
Authentication module for the dashboard using streamlit-authenticator.
"""
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

def get_authenticator() -> stauth.Authenticate:
    """
    Loads configuration from config.yaml and creates an Authenticator object.

    Returns:
        An initialized stauth.Authenticate object.
    """
    # Load configuration from YAML file
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

    # Create the authenticator object
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    return authenticator
