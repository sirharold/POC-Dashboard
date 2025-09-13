# This is a test comment to verify deployment.
import streamlit as st
import boto3
import time
import threading
import datetime
from collections import defaultdict, Counter
from copy import deepcopy
from botocore.exceptions import ClientError
from utils.helpers import load_css, create_alarm_item_html, create_alarm_legend
import yaml

# ========================================================================
# CONFIGURACIÓN
# ========================================================================
st.set_page_config(
    page_title="Dashboard EPMAPS",
    page_icon="☁️",
    layout="wide",
)

# Cargar configuración desde config.yaml
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

SHOW_AWS_ERRORS = config['settings']['show_aws_errors']
REFRESH_INTERVAL_SECONDS = config['settings']['refresh_interval_seconds']
APP_VERSION = config['settings']['version']

# ========================================================================
# LÓGICA DE ACCESO A MÚLTIPLES CUENTAS (CROSS-ACCOUNT)
# ========================================================================

def get_cross_account_boto3_client(service_name: str):
    """
    Asume el rol de la cuenta cliente y retorna un cliente de boto3 para el servicio especificado.
    """
    role_to_assume_arn = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"
    
    try:
        sts_client = boto3.client('sts')
        response = sts_client.assume_role(
            RoleArn=role_to_assume_arn,
            RoleSessionName='StreamlitDashboardSession' # Nombre de sesión requerido
        )
        
        credentials = response['Credentials']
        
        return boto3.client(
            service_name,
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )
    except ClientError as e:
        # Do not use st.error here as it's a cached function. Handle error in calling function.
        return None

@st.cache_resource(ttl=900) # Cachea las credenciales temporales por 15 minutos
def get_cross_account_boto3_client_cached(service_name: str):
    return get_cross_account_boto3_client(service_name)

def test_aws_connection():
    """
    Attempts to assume the role and create a simple STS client to test AWS connectivity.
    Returns a tuple (status_message, error_details).
    """
    role_to_assume_arn = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"
    try:
        sts_client = boto3.client('sts')
        response = sts_client.assume_role(
            RoleArn=role_to_assume_arn,
            RoleSessionName='StreamlitConnectionTestSession'
        )
        # If assume_role succeeds, we can try to get a client
        credentials = response['Credentials']
        boto3.client(
            'ec2',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )
        return "Conexión AWS OK", None
    except ClientError as e:
        return "Error de Conexión AWS", str(e)
    except Exception as e:
        return "Error Inesperado de Conexión AWS", str(e)









# ========================================================================
# FUNCIÓN PARA OBTENER DATOS DE AWS
# ========================================================================
def get_aws_data():
    """
    Fetch EC2 instances and their CloudWatch alarms from AWS.
    Returns a list of instance dictionaries with their state and alarms.
    """
    instances_data = []
    
    try:
        # Log the start of data fetching
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Starting get_aws_data()\n")
        
        # Get EC2 client
        ec2 = get_cross_account_boto3_client_cached('ec2')
        if not ec2:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Failed to get EC2 client\n")
            return []
        
        # Get CloudWatch client
        cloudwatch = get_cross_account_boto3_client_cached('cloudwatch')
        if not cloudwatch:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Failed to get CloudWatch client\n")
            return []
        
        # Fetch all EC2 instances
        response = ec2.describe_instances()
        
        # Get all CloudWatch alarms
        alarm_paginator = cloudwatch.get_paginator('describe_alarms')
        all_alarms = []
        for page in alarm_paginator.paginate():
            all_alarms.extend(page['MetricAlarms'])
        
        # Process each instance
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance.get('InstanceId', '')
                instance_state = instance.get('State', {}).get('Name', 'unknown')
                
                # Extract tags
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                
                # Only include instances with DashboardGroup tag
                if 'DashboardGroup' not in tags:
                    continue
                
                # Count alarms for this instance
                instance_alarms = Counter()
                for alarm in all_alarms:
                    dimensions = alarm.get('Dimensions', [])
                    if any(d['Name'] == 'InstanceId' and d['Value'] == instance_id for d in dimensions):
                        alarm_state = alarm.get('StateValue', 'UNKNOWN')
                        instance_alarms[alarm_state] += 1
                
                # Create instance data structure
                instance_data = {
                    'ID': instance_id,
                    'Name': tags.get('Name', instance_id),
                    'State': instance_state,
                    'Environment': tags.get('Environment', 'Unknown'),
                    'DashboardGroup': tags.get('DashboardGroup', 'Uncategorized'),
                    'Alarms': instance_alarms,
                    'PrivateIP': instance.get('PrivateIpAddress', 'N/A')
                }
                
                instances_data.append(instance_data)
        
        # Log the results
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Found {len(instances_data)} instances with DashboardGroup tag\n")
            f.write(f"[{time.ctime()}] Total alarms processed: {len(all_alarms)}\n")
        
        return instances_data
        
    except Exception as e:
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Error in get_aws_data(): {str(e)}\n")
        return []

# ========================================================================
# FUNCIONES DE LA VISTA DE DETALLES (Sin cambios)
# ========================================================================
@st.cache_data(ttl=60)
def get_instance_details(instance_id: str):
    try:
        ec2 = get_cross_account_boto3_client('ec2')
        if not ec2: return None
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if response['Reservations'] and response['Reservations'][0]['Instances']:
            return response['Reservations'][0]['Instances'][0]
        return None
    except (ClientError, IndexError):
        return None

@st.cache_data(ttl=60)
def get_alarms_for_instance(instance_id: str):
    try:
        cloudwatch = get_cross_account_boto3_client('cloudwatch')
        if not cloudwatch: return []
        paginator = cloudwatch.get_paginator('describe_alarms')
        pages = paginator.paginate()
        instance_alarms = []
        for page in pages:
            for alarm in page['MetricAlarms']:
                if any(dim['Name'] == 'InstanceId' and dim['Value'] == instance_id for dim in alarm['Dimensions']):
                    instance_alarms.append(alarm)
        return instance_alarms
    except ClientError:
        return []

@st.cache_data(ttl=60)
def get_cpu_utilization(instance_id: str):
    try:
        cloudwatch = get_cross_account_boto3_client('cloudwatch')
        if not cloudwatch: return None
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2', MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
            EndTime=datetime.datetime.utcnow(), Period=300, Statistics=['Average']
        )
        return sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0] if response['Datapoints'] else None
    except ClientError:
        return None

@st.cache_data(ttl=60)
def get_memory_utilization(instance_id: str):
    try:
        cloudwatch = get_cross_account_boto3_client('cloudwatch')
        if not cloudwatch: return None
        # Try CWAgent namespace first
        response = cloudwatch.get_metric_statistics(
            Namespace='CWAgent', MetricName='mem_used_percent',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
            EndTime=datetime.datetime.utcnow(), Period=300, Statistics=['Average']
        )
        return sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0] if response['Datapoints'] else None
    except ClientError:
        return None

@st.cache_data(ttl=60)
def get_disk_utilization(instance_id: str):
    try:
        cloudwatch = get_cross_account_boto3_client('cloudwatch')
        if not cloudwatch: return []
        
        disk_metrics = []
        # Try to get disk metrics from CWAgent
        paginator = cloudwatch.get_paginator('list_metrics')
        pages = paginator.paginate(
            Namespace='CWAgent',
            MetricName='disk_used_percent',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
        )
        
        for page in pages:
            for metric in page['Metrics']:
                # Get the device/path dimension
                device = None
                path = None
                for dim in metric['Dimensions']:
                    if dim['Name'] == 'device':
                        device = dim['Value']
                    elif dim['Name'] == 'path':
                        path = dim['Value']
                
                if device or path:
                    # Get the latest value
                    response = cloudwatch.get_metric_statistics(
                        Namespace='CWAgent',
                        MetricName='disk_used_percent',
                        Dimensions=metric['Dimensions'],
                        StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
                        EndTime=datetime.datetime.utcnow(),
                        Period=300,
                        Statistics=['Average']
                    )
                    
                    if response['Datapoints']:
                        latest = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0]
                        disk_metrics.append({
                            'device': device or path or 'Unknown',
                            'usage': latest['Average']
                        })
        
        return disk_metrics
    except ClientError:
        return []

def display_detail_page(instance_id: str):
    details = get_instance_details(instance_id)
    st.markdown("<a href='/' target='_self' style='text-decoration: none;'>← Volver al Dashboard</a>", unsafe_allow_html=True)
    if not details:
        st.error(f"No se pudieron obtener los detalles para la instancia con ID: {instance_id}")
        return
    instance_name = next((tag['Value'] for tag in details.get('Tags', []) if tag['Key'] == 'Name'), instance_id)
    st.markdown(f"<h1>Detalles de <span style='color: #00d4ff;'>{instance_name}</span></h1>", unsafe_allow_html=True)
    st.divider()
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("## ℹ️ Información General")
        st.text(f"ID: {details.get('InstanceId')}")
        st.text(f"Tipo: {details.get('InstanceType')}")
        st.text(f"Estado: {details.get('State', {}).get('Name')}")
        st.text(f"Zona: {details.get('Placement', {}).get('AvailabilityZone')}")
        st.text(f"IP Privada: {details.get('PrivateIpAddress')}")
        st.markdown("## 🚨 Alarmas")
        st.markdown(create_alarm_legend(), unsafe_allow_html=True)
        alarms = get_alarms_for_instance(instance_id)
        if alarms:
            for alarm in alarms:
                state = alarm.get('StateValue')
                color = "red" if state == "ALARM" else "gray" if state == "INSUFFICIENT_DATA" else "green"
                alarm_arn = alarm.get('AlarmArn')
                st.markdown(create_alarm_item_html(alarm.get('AlarmName'), color, alarm_arn), unsafe_allow_html=True)
        else:
            st.info("No se encontraron alarmas para esta instancia.")
    with col2:
        st.markdown("## 📊 Métricas de Rendimiento")
        
        # CPU Metric
        cpu_datapoint = get_cpu_utilization(instance_id)
        if cpu_datapoint:
            cpu_avg = round(cpu_datapoint.get('Average', 0), 2)
            st.markdown("**🖥️ Utilización de CPU (promedio 5 min)**")
            st.progress(cpu_avg / 100, f"{cpu_avg}%")
        else:
            st.info("No hay datos de CPU disponibles.")
        
        # Memory Metric
        st.markdown("---")
        memory_datapoint = get_memory_utilization(instance_id)
        if memory_datapoint:
            mem_avg = round(memory_datapoint.get('Average', 0), 2)
            st.markdown("**🧠 Utilización de Memoria RAM (promedio 5 min)**")
            st.progress(mem_avg / 100, f"{mem_avg}%")
        else:
            st.info("No hay datos de memoria disponibles. Asegúrese de que CloudWatch Agent esté instalado.")
        
        # Disk Metrics
        st.markdown("---")
        st.markdown("**💾 Utilización de Discos**")
        disk_metrics = get_disk_utilization(instance_id)
        if disk_metrics:
            for disk in disk_metrics:
                device = disk['device']
                usage = round(disk['usage'], 2)
                
                # Color code based on usage
                if usage > 95:
                    color = "🔴"
                    st.markdown(f"<div style='background-color: rgba(255,0,110,0.2); padding: 8px; border-radius: 4px; margin-bottom: 8px;'>", unsafe_allow_html=True)
                elif usage > 90:
                    color = "🟡"
                    st.markdown(f"<div style='background-color: rgba(255,183,0,0.2); padding: 8px; border-radius: 4px; margin-bottom: 8px;'>", unsafe_allow_html=True)
                else:
                    color = "🟢"
                    st.markdown(f"<div style='padding: 8px; margin-bottom: 8px;'>", unsafe_allow_html=True)
                
                st.markdown(f"{color} **{device}**")
                st.progress(usage / 100, f"{usage}%")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No hay datos de disco disponibles. Asegúrese de que CloudWatch Agent esté instalado.")

# =======================================================================
# FUNCIONES DE LA VISTA DE DASHBOARD (Modificadas)
# =======================================================================
def get_state_color_and_status(state: str):
    if state == 'running': return 'green', '99%'
    if state == 'stopped': return 'red', '0%'
    if state in ['pending', 'stopping', 'shutting-down']: return 'yellow', '50%'
    return 'grey', 'N/A'

def create_alert_bar_html(alerts_data: Counter) -> str:
    critical = alerts_data.get('ALARM', 0)
    insufficient = alerts_data.get('INSUFFICIENT_DATA', 0)
    ok = alerts_data.get('OK', 0)
    total = critical + insufficient + ok
    
    if total == 0:
        crit_pct, insuf_pct, ok_pct = 0, 0, 100
    else:
        crit_pct = (critical/total)*100
        insuf_pct = (insufficient/total)*100
        ok_pct = (ok/total)*100
    
    return f'''<div class='alert-bar-container'><div class='alert-bar'><div class='alert-bar-critical' style='width: {crit_pct}%;' title='Alarm: {critical}'></div><div class='alert-bar-insufficient' style='width: {insuf_pct}%;' title='Insufficient Data: {insufficient}'></div><div class='alert-bar-ok' style='width: {ok_pct}%;' title='OK: {ok}'></div></div><div class='alert-bar-labels'><span style='color: #ff006e;'>A: {critical}</span> <span style='color: #808080;'>I: {insufficient}</span> <span style='color: #00ff88;'>O: {ok}</span></div></div>'''

def create_server_card(instance: dict):
    vm_name = instance.get('Name', instance.get('ID', 'N/A'))
    instance_id = instance.get('ID', '')
    private_ip = instance.get('PrivateIP', 'N/A')
    state = instance.get('State', 'unknown')
    alerts = instance.get('Alarms', Counter())
    
    # Determine card color based on alarms
    if alerts.get('ALARM', 0) > 0:
        card_status = 'red'
    elif alerts.get('INSUFFICIENT_DATA', 0) > 0:
        card_status = 'gray'
    else:
        card_status = 'green'
    
    alert_bar_html = create_alert_bar_html(alerts)
    card_content = f'''<div class='server-card server-card-{card_status}'>
        <div class='server-name'>{vm_name}</div>
        <div style='font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-top: 2px;'>{private_ip}</div>
        <div style='margin-top: 12px;'>
            <div style='font-size: 0.7rem; color: rgba(255,255,255,0.8); margin-bottom: 4px; text-align: center;'>🚨 Alertas CloudWatch</div>
            {alert_bar_html}
        </div>
    </div>'''
    st.markdown(f"<a href='?poc_vm_id={instance_id}' target='_self' class='card-link'>{' '.join(card_content.split())}</a>", unsafe_allow_html=True)

def create_group_container(group_name: str, instances: list):
    # Determine group status based on all instances' alarms
    has_critical = False
    has_insufficient = False
    
    for instance in instances:
        alerts = instance.get('Alarms', Counter())
        if alerts.get('ALARM', 0) > 0:
            has_critical = True
            break
        elif alerts.get('INSUFFICIENT_DATA', 0) > 0:
            has_insufficient = True
    
    # Set group color based on worst status
    if has_critical:
        group_status = 'red'
    elif has_insufficient:
        group_status = 'gray'
    else:
        group_status = 'green'
    
    st.markdown(f"<div class='group-container group-status-{group_status}'><div class='group-title'>{group_name}</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, instance in enumerate(instances):
        with cols[idx % 3]:
            create_server_card(instance)

def display_debug_log():
    try:
        with open("/tmp/streamlit_aws_debug.log", "r") as f:
            log_content = f.read()
        st.subheader("AWS Debug Log (/tmp/streamlit_aws_debug.log)")
        st.code(log_content, language="text")
    except FileNotFoundError:
        st.warning("AWS Debug Log file not found.")
    except Exception as e:
        st.error(f"Error reading debug log: {e}")

def build_and_display_dashboard(environment: str):
    instances = deepcopy(st.session_state.data_cache["instances"])
    last_updated = st.session_state.data_cache["last_updated"]
    error_message = st.session_state.data_cache.get("error_message")

    if SHOW_AWS_ERRORS and error_message:
        st.error(f"Error de AWS: {error_message}")
        display_debug_log()

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
        
        # Arrange groups in 2 columns
        group_items = sorted(grouped_instances.items())
        col1, col2 = st.columns(2)
        
        for idx, (group_name, instance_list) in enumerate(group_items):
            if idx % 2 == 0:
                with col1:
                    create_group_container(group_name, instance_list)
            else:
                with col2:
                    create_group_container(group_name, instance_list)
    

def display_dashboard_page():
    # Initialize st.session_state.data_cache if it doesn't exist
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {"instances": [], "last_updated": None, "connection_status": "Desconocido", "connection_error": None, "error_message": None}

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
        st.markdown(f"<h1 style='text-align: center;'>Dashboard {current_env}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size: 0.8em; color: grey;'>Esta página se autorecarga cada {REFRESH_INTERVAL_SECONDS} segundos {APP_VERSION}</p>", unsafe_allow_html=True)
        
        # Add meta refresh to auto-reload the page
        st.markdown(f'<meta http-equiv="refresh" content="{REFRESH_INTERVAL_SECONDS}">', unsafe_allow_html=True)
    
    st.divider()

    # Add alarm legend
    st.markdown(create_alarm_legend(), unsafe_allow_html=True)

    # Fetch data directly in the main thread
    connection_status_msg, connection_error_details = test_aws_connection()
    st.session_state.data_cache["connection_status"] = connection_status_msg
    st.session_state.data_cache["connection_error"] = connection_error_details

    if connection_status_msg == "Conexión AWS OK":
        instances_data = get_aws_data()
        st.session_state.data_cache["instances"] = instances_data
        st.session_state.data_cache["last_updated"] = time.time()
    else:
        st.session_state.data_cache["instances"] = []
        st.session_state.data_cache["last_updated"] = None

    # --- Renderizado del Dashboard ---
    build_and_display_dashboard(current_env)

# ========================================================================
# LÓGICA PRINCIPAL (ROUTER)
# ========================================================================



# 2. Cargar CSS
load_css()

# 3. Router principal: decidir qué vista mostrar basado en la URL
if 'poc_vm_id' in st.query_params:
    display_detail_page(st.query_params['poc_vm_id'])
else:
    display_dashboard_page()