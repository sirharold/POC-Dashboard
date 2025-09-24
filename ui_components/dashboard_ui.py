"""
Dashboard UI Components that preserve the exact original UI behavior and appearance.
"""
import streamlit as st
from collections import defaultdict, Counter
from copy import deepcopy
import time
from utils.helpers import load_css, create_alarm_item_html, create_alarm_legend


class DashboardUI:
    """Manages dashboard UI components, preserving original appearance and behavior."""
    
    def __init__(self, aws_service):
        """Initialize with AWS service dependency."""
        self.aws_service = aws_service
    
    def get_state_color_and_status(self, state: str):
        """Same logic as original function."""
        if state == 'running': return 'green', '99%'
        if state == 'stopped': return 'red', '0%'
        if state in ['pending', 'stopping', 'shutting-down']: return 'yellow', '50%'
        return 'grey', 'N/A'

    def create_alert_bar_html(self, alerts_data: Counter) -> str:
        """Generate alert bar HTML. Exact same logic as original function."""
        critical = alerts_data.get('ALARM', 0)
        preventive = alerts_data.get('PREVENTIVE', 0)
        insufficient = alerts_data.get('INSUFFICIENT_DATA', 0) + alerts_data.get('UNKNOWN', 0)
        ok = alerts_data.get('OK', 0)
        total = critical + preventive + insufficient + ok
        
        if total == 0:
            crit_pct, prev_pct, insuf_pct, ok_pct = 0, 0, 0, 100
        else:
            crit_pct = (critical/total)*100
            prev_pct = (preventive/total)*100
            insuf_pct = (insufficient/total)*100
            ok_pct = (ok/total)*100
        
        return f'''<div class='alert-bar-container'><div class='alert-bar'><div class='alert-bar-critical' style='width: {crit_pct}%;' title='Alarm: {critical}'></div><div class='alert-bar-preventive' style='width: {prev_pct}%; background-color: #ffb700;' title='Preventive: {preventive}'></div><div class='alert-bar-insufficient' style='width: {insuf_pct}%;' title='Insufficient Data: {insufficient}'></div><div class='alert-bar-ok' style='width: {ok_pct}%;' title='OK: {ok}'></div></div><div class='alert-bar-labels'><span style='color: #ff006e;'>A: {critical}</span> <span style='color: #ffb700;'>P: {preventive}</span> <span style='color: #808080;'>I: {insufficient}</span> <span style='color: #00ff88;'>O: {ok}</span></div></div>'''

    def create_server_card(self, instance: dict):
        """Create server card. Exact same logic as original function."""
        vm_name = instance.get('Name', instance.get('ID', 'N/A'))
        instance_id = instance.get('ID', '')
        private_ip = instance.get('PrivateIP', 'N/A')
        state = instance.get('State', 'unknown')
        alerts = instance.get('Alarms', Counter())
        
        # Determine card color based on alarms - new logic
        if alerts.get('ALARM', 0) > 0:
            card_status = 'red'
        elif alerts.get('INSUFFICIENT_DATA', 0) > 0 or alerts.get('UNKNOWN', 0) > 0:
            card_status = 'gray'
        else:
            # If only green and yellow alarms, show green
            card_status = 'green'
        
        alert_bar_html = self.create_alert_bar_html(alerts)
        card_content = f'''<div class='server-card server-card-{card_status}'>
            <div class='server-name'>{vm_name}</div>
            <div style='font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-top: 2px;'>{private_ip}</div>
            <div style='margin-top: 12px;'>
                <div style='font-size: 0.7rem; color: rgba(255,255,255,0.8); margin-bottom: 4px; text-align: center;'>🚨 Alertas CloudWatch</div>
                {alert_bar_html}
            </div>
        </div>'''
        
        # Preserve columns parameter when navigating to detail page
        columns_param = st.query_params.get('columns', '2')
        
        # Use HTML link - session persistence will handle authentication
        st.markdown(f"<a href='?poc_vm_id={instance_id}&columns={columns_param}' target='_self' class='card-link'>{' '.join(card_content.split())}</a>", unsafe_allow_html=True)

    def create_group_container(self, group_name: str, instances: list):
        """Create group container. Exact same logic as original function."""
        # Determine group status based on all instances' alarms - new logic
        has_critical = False
        has_insufficient = False
        
        for instance in instances:
            alerts = instance.get('Alarms', Counter())
            if alerts.get('ALARM', 0) > 0:
                has_critical = True
                break
            elif alerts.get('INSUFFICIENT_DATA', 0) > 0 or alerts.get('UNKNOWN', 0) > 0:
                has_insufficient = True
        
        # Set group color based on worst status (no yellow for groups)
        if has_critical:
            group_status = 'red'
        elif has_insufficient:
            group_status = 'gray'
        else:
            # If only green and yellow alarms, show green
            group_status = 'green'
        
        st.markdown(f"<div class='group-container group-status-{group_status}'><div class='group-title'>{group_name}</div></div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, instance in enumerate(instances):
            with cols[idx % 3]:
                self.create_server_card(instance)

    def display_debug_log(self):
        """Display debug log. Same as original function."""
        try:
            with open("/tmp/streamlit_aws_debug.log", "r") as f:
                log_content = f.read()
            st.subheader("AWS Debug Log (/tmp/streamlit_aws_debug.log)")
            st.code(log_content, language="text")
        except FileNotFoundError:
            st.warning("AWS Debug Log file not found.")
        except Exception as e:
            st.error(f"Error reading debug log: {e}")

    def build_and_display_dashboard(self, environment: str, show_aws_errors: bool):
        """Build and display dashboard. Exact same logic as original function."""
        instances = deepcopy(st.session_state.data_cache["instances"])
        last_updated = st.session_state.data_cache["last_updated"]
        error_message = st.session_state.data_cache.get("error_message")

        if show_aws_errors and error_message:
            st.error(f"Error de AWS: {error_message}")
            self.display_debug_log()

        # Log _data_cache content for debugging
        connection_status = st.session_state.data_cache.get("connection_status", "Desconocido")
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Main thread: _data_cache instances count: {len(instances)}, connection_status: {connection_status}\n")

        if not instances:
            st.info("Cargando datos desde AWS... La primera actualización puede tardar hasta 30 segundos.")
            return
        
        # Filtra las instancias por el entorno seleccionado
        filtered_instances = [inst for inst in instances if inst.get('Environment') == environment]

        if not filtered_instances:
            st.warning(f"No se encontraron instancias con el tag 'Environment={environment}'.")
        else:
            grouped_instances = defaultdict(list)
            for instance in filtered_instances:
                grouped_instances[instance.get('DashboardGroup') or 'Uncategorized'].append(instance)
            
            # Arrange groups in selected number of columns
            group_items = sorted(grouped_instances.items())
            
            
            num_columns = int(st.query_params.get('columns', 2))
            if num_columns not in [1, 2, 3, 4]:
                num_columns = 2
            
            if num_columns == 1:
                # Single column layout
                for group_name, instance_list in group_items:
                    self.create_group_container(group_name, instance_list)
            else:
                # Multi-column layout
                columns = st.columns(num_columns)
                for idx, (group_name, instance_list) in enumerate(group_items):
                    with columns[idx % num_columns]:
                        self.create_group_container(group_name, instance_list)

    def display_dashboard_page(self, refresh_interval: int, app_version: str, show_aws_errors: bool):
        """Main dashboard page. Exact same logic as original function."""
        # Initialize st.session_state.data_cache if it doesn't exist
        if 'data_cache' not in st.session_state:
            st.session_state.data_cache = {
                "instances": [], 
                "last_updated": None, 
                "connection_status": "Desconocido", 
                "connection_error": None, 
                "error_message": None
            }

        # --- Lógica de Navegación de Entornos ---
        ENVIRONMENTS = ["Production", "QA", "DEV"]
        if 'env_index' not in st.session_state:
            st.session_state.env_index = 0

        nav_cols = st.columns([1, 10, 1])
        with nav_cols[0]:
            if st.button("←", use_container_width=True):
                st.session_state.env_index = (st.session_state.env_index - 1) % len(ENVIRONMENTS)
                st.rerun()
        with nav_cols[2]:
            if st.button("→", use_container_width=True):
                st.session_state.env_index = (st.session_state.env_index + 1) % len(ENVIRONMENTS)
                st.rerun()
        
        current_env = ENVIRONMENTS[st.session_state.env_index]
        with nav_cols[1]:
            st.markdown(f"<h2 style='text-align: center; margin: 0; padding: 0;'>{current_env}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; font-size: 0.75em; color: grey; margin: 0; padding: 0;'>Esta página se actualiza cada {refresh_interval} segundos {app_version}</p>", unsafe_allow_html=True)
            # Add alarm report link
            col_center = st.columns([1, 1, 1])
            with col_center[1]:
                if st.button("📊 Reporte Alarmas", use_container_width=True, type="secondary"):
                    st.query_params.update({"alarm_report": "true"})
                    st.rerun()
        
        st.divider()

        # Add column control and alarm legend
        control_cols = st.columns([1, 3])
        
        # Get column count from query params or default
        current_columns = int(st.query_params.get('columns', 2))
        if current_columns not in [1, 2, 3, 4]:
            current_columns = 2
        
        with control_cols[0]:
            # Create columns for label and selectbox
            label_col, select_col = st.columns([1, 2])
            with label_col:
                st.markdown("<div style='padding-top: 0.3rem; font-weight: 600;'>Columnas:</div>", unsafe_allow_html=True)
            with select_col:
                selected_columns = st.selectbox(
                    label="Columnas",  # Proper label for accessibility
                    options=[1, 2, 3, 4],
                    index=[1, 2, 3, 4].index(current_columns),
                    key="column_selector",
                    label_visibility="hidden"
                )
                # Update query params when selection changes
                if selected_columns != current_columns:
                    st.query_params['columns'] = str(selected_columns)
                    st.rerun()
        
        with control_cols[1]:
            st.markdown(create_alarm_legend(), unsafe_allow_html=True)

        # Use fragment with auto-refresh for smooth updates
        self._render_dashboard_content(current_env, show_aws_errors, refresh_interval)

    @st.fragment(run_every=30)  # Auto-refresh every 30 seconds
    def _render_dashboard_content(self, current_env: str, show_aws_errors: bool, refresh_interval: int):
        """Render dashboard content with auto-refresh using st.fragment"""
        # Only refresh if we're still on the dashboard (not detail page)
        if 'poc_vm_id' in st.query_params:
            return  # Don't refresh on detail pages
        
        # Fetch data
        connection_status_msg, connection_error_details = self.aws_service.test_aws_connection()
        st.session_state.data_cache["connection_status"] = connection_status_msg
        st.session_state.data_cache["connection_error"] = connection_error_details

        if connection_status_msg == "Conexión AWS OK":
            instances_data = self.aws_service.get_aws_data()
            st.session_state.data_cache["instances"] = instances_data
            st.session_state.data_cache["last_updated"] = time.time()
        else:
            st.session_state.data_cache["instances"] = []
            st.session_state.data_cache["last_updated"] = None

        # --- Renderizado del Dashboard ---
        self.build_and_display_dashboard(current_env, show_aws_errors)