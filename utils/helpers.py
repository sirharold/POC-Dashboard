"""
Utility functions for the SAP Infrastructure Dashboard
"""
import streamlit as st
from urllib.parse import quote
import random
import yaml
import html

# ========================================================================
# DATA MODELS AND CONFIGURATIONS
# ========================================================================

@st.cache_data(ttl=3600)
def load_config() -> dict:
    """
    Load server configurations from config.yaml.
    The result is cached to avoid reading the file on every script run.
    
    Returns:
        dict: A dictionary with the app configuration.
    """
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError) as e:
        # Use print in a helper to avoid Streamlit command errors on import
        print(f"Error loading config.yaml: {e}")
        return {}

ALERT_PATTERNS = [
    {"critical": 0, "warning": 2, "ok": 8},
    {"critical": 5, "warning": 3, "ok": 2},
    {"critical": 1, "warning": 4, "ok": 5},
    {"critical": 0, "warning": 1, "ok": 9},
    {"critical": 2, "warning": 3, "ok": 5},
    {"critical": 3, "warning": 2, "ok": 5},
    {"critical": 0, "warning": 0, "ok": 10}
]

STATUS_COLORS = {
    "green": "#00ff88",
    "red": "#ff006e", 
    "yellow": "#ffb700"
}

# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================


@st.cache_data(ttl=60)
def get_vm_alerts(vm_name: str) -> dict:
    """
    Get alert distribution for a virtual machine.
    
    Args:
        vm_name (str): Name of the virtual machine
        
    Returns:
        dict: Dictionary with critical, warning, and ok alert counts
    """
    return ALERT_PATTERNS[hash(vm_name) % len(ALERT_PATTERNS)]

def get_status_color(status: str) -> str:
    """
    Get hex color code for a status.
    
    Args:
        status (str): Status ('green', 'yellow', 'red')
        
    Returns:
        str: Hex color code
    """
    return STATUS_COLORS.get(status, "#808080")

def calculate_availability(status: str) -> str:
    """
    Calculate availability percentage based on status.
    
    Args:
        status (str): VM status
        
    Returns:
        str: Availability percentage
    """
    availability_map = {
        "green": "99%",
        "yellow": "95%", 
        "red": "85%"
    }
    return availability_map.get(status, "90%")

@st.cache_data(ttl=60)
def get_sample_alarms(vm_name: str) -> list:
    """
    Get sample alarm data for a VM.
    
    Args:
        vm_name (str): Name of the virtual machine
        
    Returns:
        list: List of tuples (alarm_name, status)
    """
    base_alarms = [
        ("CPU Alta", "red"),
        ("Memoria OK", "green"),
        ("Disco C: Casi Lleno", "yellow"),
        ("Red Estable", "green"),
        ("Backup", "green"),
        ("Antivirus", "green")
    ]
    
    # Add specific alarms based on VM name
    if "PRD" in vm_name:
        base_alarms.append(("Servicio SAP", "red" if vm_name == "SRVISUPRD" else "green"))
    
    if "BDD" in vm_name or "DB" in vm_name:
        base_alarms.append(("Base de Datos", "yellow"))
        
    return base_alarms

@st.cache_data(ttl=60)
def get_sample_cpu_data(cores: int = 4) -> list:
    """
    Generate sample CPU usage data.
    
    Args:
        cores (int): Number of CPU cores
        
    Returns:
        list: List of CPU usage percentages
    """
    return [random.randint(20, 90) for _ in range(cores)]

@st.cache_data(ttl=60)
def get_sample_disk_data() -> list:
    """
    Generate sample disk usage data.
    
    Returns:
        list: List of tuples (disk_name, usage_percent, capacity)
    """
    return [
        ("C:", 75, "120GB"),
        ("D:", 45, "500GB"),
        ("E:", 90, "1TB"),
        ("F:", 30, "2TB"),
        ("G:", 60, "500GB")
    ]

@st.cache_data(ttl=60)
def get_sample_ram_usage() -> int:
    """
    Generate sample RAM usage percentage.
    
    Returns:
        int: RAM usage percentage
    """
    return random.randint(40, 85)

# ========================================================================
# CHART CREATION FUNCTIONS
# ========================================================================

# ========================================================================
# HTML GENERATION FUNCTIONS
# ========================================================================

@st.cache_data
def load_css():
    """
    Load CSS styles from external file.
    """
    try:
        with open('assets/styles.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. Using minimal styles.")
        st.markdown("<style>.stApp { background: #0a0f1c; }</style>", unsafe_allow_html=True)

def create_alert_bar_html(alerts_data: dict) -> str:
    """
    Generate HTML for a segmented alert proportion bar.
    
    Args:
        alerts_data (dict): Dictionary with critical, warning, and ok alert counts
        
    Returns:
        str: HTML string for the alert bar
    """
    critical = alerts_data.get('critical', 0)
    warning = alerts_data.get('warning', 0)
    ok = alerts_data.get('ok', 0)
    total = critical + warning + ok
    
    if total == 0:
        crit_pct, warn_pct, ok_pct = 0, 0, 100
    else:
        crit_pct = (critical / total) * 100
        warn_pct = (warning / total) * 100
        ok_pct = (ok / total) * 100
    
    return f"""
    <div class='alert-bar-container'>
        <div class='alert-bar'>
            <div class='alert-bar-critical' style='width: {crit_pct}%;' title='Critical: {critical}'></div>
            <div class='alert-bar-warning' style='width: {warn_pct}%;' title='Warning: {warning}'></div>
            <div class='alert-bar-ok' style='width: {ok_pct}%;' title='OK: {ok}'></div>
        </div>
        <div class='alert-bar-labels'>
            <span style='color: #ff006e;'>C: {critical}</span>
            <span style='color: #ffb700;'>W: {warning}</span>
            <span style='color: #00ff88;'>OK: {ok}</span>
        </div>
    </div>
    """

def create_server_card_html(vm_name: str, status: str, availability: str, alerts_data: dict) -> str:
    """
    Generate HTML for a server card.
    
    Args:
        vm_name (str): Server name
        status (str): Server status
        availability (str): Availability percentage
        alerts_data (dict): Dictionary with alert counts
        
    Returns:
        str: Cleaned HTML string for the server card, wrapped in a link.
    """
    alert_bar_html = create_alert_bar_html(alerts_data)
    
    # URL-encode the vm_name to handle special characters
    encoded_vm_name = quote(vm_name)
    
    card_content = f"""
        <div class='server-card server-card-{status}'>
            <div class='server-name'>{vm_name}</div>
            <div style='display: flex; align-items: center; justify-content: space-between; margin-top: 8px; gap: 12px;'>
                <div style='flex: 0 0 auto; text-align: center;'>
                    <div style='font-size: 0.7rem; color: rgba(255,255,255,0.8); margin-bottom: 4px;'>⚡ Uptime</div>
                    <div style='font-size: 1.1rem; color: white; font-weight: 700;'>{availability}</div>
                </div>
                <div style='flex: 1; min-width: 0;'>
                    <div style='font-size: 0.7rem; color: rgba(255,255,255,0.8); margin-bottom: 4px; text-align: center;'>🚨 Alertas</div>
                    {alert_bar_html}
                </div>
            </div>
        </div>
    """
    
    # Wrap the card in an anchor tag and clean up whitespace to prevent rendering issues
    html_string = f"<a href='?selected_vm={encoded_vm_name}' target='_self' class='card-link'>{card_content}</a>"
    return " ".join(html_string.split())

def create_env_switcher_header(current_env: str):
    """
    Creates a header with navigation arrows to switch between environments.
    
    Args:
        current_env (str): The current environment ('Production', 'QA', 'DEV').
    """
    environments = {
        "Production": {"prev": "pages/3_DEV.py", "next": "pages/2_QA.py"},
        "QA": {"prev": "pages/1_Production.py", "next": "pages/3_DEV.py"},
        "DEV": {"prev": "pages/2_QA.py", "next": "pages/1_Production.py"}
    }
    
    if current_env not in environments:
        st.markdown(f"<h1>Dashboard de Infraestructura EPMAPS {current_env}</h1>", unsafe_allow_html=True)
        return

    nav = environments[current_env]
    
    # Use st.columns for layout and markdown for custom link appearance
    col1, col2, col3 = st.columns([1, 10, 1])

    with col1:
        st.page_link(nav['prev'], label="ᐊ", use_container_width=True)

    with col2:
        st.markdown(f"<h1 style='text-align: center; margin: 0;'>Dashboard de Infraestructura EPMAPS {current_env}</h1>", unsafe_allow_html=True)

    with col3:
        st.page_link(nav['next'], label="ᐅ", use_container_width=True)

def create_group_container_html(group_name: str, css_class: str) -> str:
    """
    Generate HTML for a group container.
    
    Args:
        group_name (str): Name of the group
        css_class (str): CSS class for styling
        
    Returns:
        str: HTML string for the group container
    """
    return f"""
    <div class='group-container {css_class}'>
        <div class='group-title'>{group_name}</div>
    </div>
    """

def create_alarm_item_html(alarm_name: str, status: str, alarm_arn: str = None) -> str:
    """
    Generate HTML for an alarm item.
    
    Args:
        alarm_name (str): Name of the alarm
        status (str): Status of the alarm
        alarm_arn (str): ARN of the alarm for AWS console link
        
    Returns:
        str: HTML string for the alarm item
    """
    status_icon = "🔴" if status == "red" else "🟡" if status == "yellow" else "⚫" if status == "gray" else "🟢"
    
    # Generate AWS console link if ARN is provided
    if alarm_arn:
        # Extract account ID and region from ARN (format: arn:aws:cloudwatch:region:account:alarm:name)
        try:
            arn_parts = alarm_arn.split(':')
            region = arn_parts[3] if len(arn_parts) > 3 else 'us-east-1'
            account_id = arn_parts[4] if len(arn_parts) > 4 else '011528297340'
            
            # Create the encoded search parameter for the URL
            # Replace special characters for URL encoding (more comprehensive)
            encoded_search = alarm_name.replace(' ', '*20').replace('-', '*20').replace('(', '*28').replace(')', '*29').replace('+', '*20').replace('%', '*25').replace('>', '*3E').replace('<', '*3C').replace('&', '*26').replace('=', '*3D')
            
            # Generate the CloudWatch console URL in the correct format
            # Use quote with safe='' to ensure all special characters are encoded
            console_url = f"https://{account_id}-pdl6i3zc.{region}.console.aws.amazon.com/cloudwatch/home?region={region}#alarmsV2:alarm/{quote(alarm_name, safe='')}?~(search~'{encoded_search}')"
            
            # HTML escape the alarm name for safe display
            escaped_alarm_name = html.escape(alarm_name)
            
            return f'''
            <div class="alarm-item">
                <a href="{console_url}" target="_blank" style="color: white; text-decoration: none; font-weight: 500;">
                    {escaped_alarm_name} 🔗
                </a>
                <span style="font-size: 1.5rem;">{status_icon}</span>
            </div>
            '''
        except:
            pass
    
    # HTML escape the alarm name for safe display (fallback case)
    escaped_alarm_name = html.escape(alarm_name)
    
    return f'''
    <div class="alarm-item">
        <span style="color: white; font-weight: 500;">{escaped_alarm_name}</span>
        <span style="font-size: 1.5rem;">{status_icon}</span>
    </div>
    '''

def create_alarm_legend() -> str:
    """
    Generate HTML for the alarm color legend in a single line.
    
    Returns:
        str: HTML string for the alarm legend
    """
    return """
    <div style='background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 8px 16px; margin: 12px 0; backdrop-filter: blur(10px);'>
        <div style='display: flex; align-items: center; justify-content: center; gap: 20px; flex-wrap: wrap;'>
            <span style='color: white; font-weight: 600; font-size: 0.9rem;'>Alarmas:</span>
            <div style='display: flex; align-items: center; gap: 6px;'>
                <div style='width: 10px; height: 10px; background-color: #ff006e; border-radius: 50%;'></div>
                <span style='color: rgba(255, 255, 255, 0.9); font-size: 0.8rem;'>En Alarma</span>
            </div>
            <div style='display: flex; align-items: center; gap: 6px;'>
                <div style='width: 10px; height: 10px; background-color: #ffb700; border-radius: 50%;'></div>
                <span style='color: rgba(255, 255, 255, 0.9); font-size: 0.8rem;'>Preventivas</span>
            </div>
            <div style='display: flex; align-items: center; gap: 6px;'>
                <div style='width: 10px; height: 10px; background-color: #808080; border-radius: 50%;'></div>
                <span style='color: rgba(255, 255, 255, 0.9); font-size: 0.8rem;'>Sin Datos</span>
            </div>
            <div style='display: flex; align-items: center; gap: 6px;'>
                <div style='width: 10px; height: 10px; background-color: #00ff88; border-radius: 50%;'></div>
                <span style='color: rgba(255, 255, 255, 0.9); font-size: 0.8rem;'>Normal</span>
            </div>
        </div>
    </div>
    """