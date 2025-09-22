"""
Dashboard Manager class that coordinates all components while preserving original UI.
"""
import streamlit as st
import yaml
from services.aws_service import AWSService
from ui_components.dashboard_ui import DashboardUI
from ui_components.detail_ui import DetailUI
from ui_components.alarm_report_ui import AlarmReportUI
from utils.helpers import load_css


class DashboardManager:
    """Main dashboard manager that coordinates all components."""
    
    def __init__(self):
        """Initialize dashboard manager with all components."""
        # Load configuration
        with open("config.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        
        # Initialize services
        self.aws_service = AWSService()
        
        # Initialize UI components
        self.dashboard_ui = DashboardUI(self.aws_service)
        self.detail_ui = DetailUI(self.aws_service)
        self.alarm_report_ui = AlarmReportUI(self.aws_service)
        
        # Configuration values
        self.show_aws_errors = self.config['settings']['show_aws_errors']
        self.refresh_interval = self.config['settings']['refresh_interval_seconds']
        self.app_version = self.config['settings']['version']
    
    def run(self):
        """Main entry point that routes to appropriate page."""
        # Set page config with CloudFront compatibility headers
        st.set_page_config(
            page_title="Dashboard EPMAPS",
            page_icon="☁️",
            layout="wide",
        )
        
        # Add CloudFront compatibility headers
        if 'cloudfront_headers_set' not in st.session_state:
            # Force disable XSRF protection for CloudFront
            st.markdown("""
                <script>
                    window.streamlitConfig = {
                        server: {
                            enableXsrfProtection: false,
                            enableCORS: false
                        }
                    };
                </script>
            """, unsafe_allow_html=True)
            st.session_state.cloudfront_headers_set = True
        
        # Load CSS (same as original)
        load_css()
        
        # Router principal: decidir qué vista mostrar basado en la URL
        if 'alarm_report' in st.query_params:
            self.alarm_report_ui.display_alarm_report()
        elif 'poc_vm_id' in st.query_params:
            self.detail_ui.display_detail_page(st.query_params['poc_vm_id'])
        else:
            self.dashboard_ui.display_dashboard_page(
                self.refresh_interval, 
                self.app_version, 
                self.show_aws_errors
            )