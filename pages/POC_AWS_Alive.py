"""
POC Page with Boto3 and Shared Cache for Multi-User Real-Time AWS Data
"""
import streamlit as st
import boto3
import time
import threading
from collections import defaultdict, Counter
from copy import deepcopy
from botocore.exceptions import ClientError
from utils.helpers import load_css

# =======================================================================
# SHARED CACHE AND BACKGROUND THREAD SETUP
# =======================================================================

_data_cache = {"instances": [], "last_updated": None}
_lock = threading.Lock()

def get_aws_data():
    """
    Fetches all necessary data from AWS using boto3.
    Called by the background thread.
    """
    try:
        # Use the default session, which will use the IAM role in a deployed environment
        ec2 = boto3.client('ec2', region_name='us-east-1')
        cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

        # Fetch instances with the DashboardGroup tag
        paginator = ec2.get_paginator('describe_instances')
        instance_pages = paginator.paginate(
            Filters=[{'Name': 'tag-key', 'Values': ['DashboardGroup']}]
        )

        instances_list = []
        for page in instance_pages:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                    instances_list.append({
                        'ID': instance['InstanceId'],
                        'Name': tags.get('Name', instance['InstanceId']),
                        'State': instance['State']['Name'],
                        'DashboardGroup': tags.get('DashboardGroup', 'Uncategorized')
                    })
        
        # Debugging: Log the raw response and processed list
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Raw EC2 response (first page): {list(instance_pages)[0] if instance_pages else 'No pages'}\n")
            f.write(f"[{time.ctime()}] Processed instances_list: {instances_list}\n")
        
        # Fetch all alarms and map them to instances in memory for efficiency
        alarm_paginator = cloudwatch.get_paginator('describe_alarms')
        alarm_pages = alarm_paginator.paginate()
        instance_alarms = defaultdict(list)
        for page in alarm_pages:
            for alarm in page['MetricAlarms']:
                for dimension in alarm['Dimensions']:
                    if dimension['Name'] == 'InstanceId':
                        instance_alarms[dimension['Value']].append(alarm['StateValue'])
                        break
        
        # Attach alarm counts to each instance
        for instance in instances_list:
            instance['Alarms'] = Counter(instance_alarms.get(instance['ID'], []))

        return instances_list

    except ClientError as e:
        # Log to a file for debugging
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Boto3 ClientError: {e}\n")
        return []
    except Exception as e:
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] An unexpected error occurred in get_aws_data: {e}\n")
        return []

def update_cache_in_background(interval_seconds: int):
    """Daemon thread to periodically fetch data and update the shared cache."""
    while True:
        instances_data = get_aws_data()
        with _lock:
            _data_cache["instances"] = instances_data
            _data_cache["last_updated"] = time.time()
        time.sleep(interval_seconds)

# =======================================================================
# UI RENDERING FUNCTIONS
# =======================================================================

def get_state_color_and_status(state: str):
    if state == 'running': return 'green', '99%'
    if state == 'stopped': return 'red', '0%'
    if state in ['pending', 'stopping', 'shutting-down']: return 'yellow', '50%'
    return 'grey', 'N/A'

def create_alert_bar_html(alerts_data: Counter) -> str:
    critical = alerts_data.get('ALARM', 0)
    warning = alerts_data.get('INSUFFICIENT_DATA', 0)
    ok = alerts_data.get('OK', 0)
    total = critical + warning + ok
    crit_pct, warn_pct, ok_pct = (0, 0, 100) if total == 0 else ((critical/total)*100, (warning/total)*100, (ok/total)*100)
    return f"""<div class='alert-bar-container'><div class='alert-bar'><div class='alert-bar-critical' style='width: {crit_pct}%;' title='Alarm: {critical}'></div><div class='alert-bar-warning' style='width: {warn_pct}%;' title='Insufficient Data: {warning}'></div><div class='alert-bar-ok' style='width: {ok_pct}%;' title='OK: {ok}'></div></div><div class='alert-bar-labels'><span style='color: #ff006e;'>A: {critical}</span> <span style='color: #ffb700;'>I: {warning}</span> <span style='color: #00ff88;'>O: {ok}</span></div></div>"""

def create_server_card(instance: dict):
    vm_name = instance.get('Name', instance.get('ID', 'N/A'))
    instance_id = instance.get('ID', '')
    state = instance.get('State', 'unknown')
    alerts = instance.get('Alarms', Counter())
    status_color, availability = get_state_color_and_status(state)
    alert_bar_html = create_alert_bar_html(alerts)
    card_content = f"""<div class='server-card server-card-{status_color}'><div class='server-name'>{vm_name}</div><div style='display: flex; align-items: center; justify-content: space-between; margin-top: 8px; gap: 12px;'><div style='flex: 0 0 auto; text-align: center;'><div style='font-size: 0.7rem; color: rgba(255,255,255,0.8); margin-bottom: 4px;'>⚡ Uptime</div><div style='font-size: 1.1rem; color: white; font-weight: 700;'>{availability}</div></div><div style='flex: 1; min-width: 0;'><div style='font-size: 0.7rem; color: rgba(255,255,255,0.8); margin-bottom: 4px; text-align: center;'>🚨 Alertas CloudWatch</div>{alert_bar_html}</div></div></div>"""
    st.markdown(f"<a href='?poc_vm_id={instance_id}' target='_self' class='card-link'>{' '.join(card_content.split())}</a>", unsafe_allow_html=True)

def create_group_container(group_name: str, instances: list):
    css_classes = ["group-isu", "group-erp", "group-solman", "group-bo", "group-bw", "group-crm", "group-dc", "group-mcf", "group-po", "group-sao", "group-otros"]
    css_class = css_classes[hash(group_name) % len(css_classes)]
    st.markdown(f"<div class='group-container {css_class}'><div class='group-title'>{group_name}</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, instance in enumerate(instances):
        with cols[idx % 3]:
            create_server_card(instance)

# =======================================================================
# MAIN APPLICATION LOGIC
# =======================================================================

def build_dashboard_from_cache():
    with _lock:
        instances = deepcopy(_data_cache["instances"])
        last_updated = _data_cache["last_updated"]

    if not instances and not last_updated: # Show only on first run
        st.info("Cargando datos desde AWS... La primera actualización puede tardar hasta 30 segundos.")
        return None
    elif not instances and last_updated:
        st.warning("No se encontraron instancias con la etiqueta 'DashboardGroup' en la última actualización.")
        return last_updated

    grouped_instances = defaultdict(list)
    for instance in instances:
        grouped_instances[instance.get('DashboardGroup') or 'Uncategorized'].append(instance)

    for group_name, instance_list in sorted(grouped_instances.items()):
        create_group_container(group_name, instance_list)
    
    return last_updated

def main():
    REFRESH_INTERVAL = 30
    load_css()

    if "poc_vm_id" in st.query_params:
        st.session_state.poc_vm_id = st.query_params["poc_vm_id"]
        st.switch_page("pages/_5_POC_Detalles.py")

    title_col, timer_col = st.columns([4, 1])
    title_col.markdown("<h1>☁️ POC - AWS Live 10v</h1>", unsafe_allow_html=True)
    timer_placeholder = timer_col.empty()
    
    dashboard_placeholder = st.empty()

    while True:
        with dashboard_placeholder.container():
            last_updated = build_dashboard_from_cache()
        
        if last_updated:
            for _ in range(REFRESH_INTERVAL):
                time_since_update = int(time.time() - last_updated)
                timer_placeholder.markdown(f"<div style='font-size: 1.2rem; text-align: right; color: grey; padding-top: 1.5rem;'>Última Act: {time_since_update}s atrás</div>", unsafe_allow_html=True)
                time.sleep(1)
        else:
            time.sleep(1)

if __name__ == "__main__":
    if "cache_thread_started" not in st.session_state:
        thread = threading.Thread(target=update_cache_in_background, args=(30,), daemon=True)
        thread.start()
        st.session_state.cache_thread_started = True
    
    main()