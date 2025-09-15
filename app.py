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
import plotly.graph_objects as go
import pandas as pd

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
        
        # Get all CloudWatch alarms ONCE (more efficient)
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Getting all CloudWatch alarms...\n")
        
        alarm_paginator = cloudwatch.get_paginator('describe_alarms')
        all_alarms = []
        for page in alarm_paginator.paginate():
            all_alarms.extend(page['MetricAlarms'])
        
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Retrieved {len(all_alarms)} total alarms\n")
        
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
                
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] Processing instance {instance_id} ({tags.get('Name', 'NoName')})\n")
                
                # Count alarms for this instance
                instance_alarms = Counter()
                for alarm in all_alarms:
                    dimensions = alarm.get('Dimensions', [])
                    if any(d['Name'] == 'InstanceId' and d['Value'] == instance_id for d in dimensions):
                        alarm_state = alarm.get('StateValue', 'UNKNOWN')
                        alarm_name = alarm.get('AlarmName', '')
                        
                        # Log each alarm for debugging
                        with open("/tmp/streamlit_aws_debug.log", "a") as f:
                            f.write(f"[{time.ctime()}] Alarm: {alarm_name}, State: {alarm_state}, Instance: {instance_id}\n")
                        
                        # Check if this is a preventive alarm
                        if alarm_state == 'ALARM' and ('ALERTA' in alarm_name.upper() or 'PROACTIVA' in alarm_name.upper()):
                            instance_alarms['PREVENTIVE'] += 1
                        else:
                            instance_alarms[alarm_state] += 1
                
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] Instance {instance_id} has {len(instance_alarms)} alarm states: {dict(instance_alarms)}\n")
                
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
                    # Filter out tmpfs and other non-physical filesystems
                    disk_name = device or path or 'Unknown'
                    if any(exclude in disk_name.lower() for exclude in ['tmpfs', 'devtmpfs', 'udev', 'proc', 'sys', 'run']):
                        continue
                    
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
                            'device': disk_name,
                            'usage': latest['Average']
                        })
        
        return disk_metrics
    except ClientError:
        return []

def create_gauge(value, title, max_value=100):
    """Create a gauge chart using plotly"""
    # Determine color based on value
    if value < 80:
        color = "green"
    elif value < 92:
        color = "yellow"
    else:
        color = "red"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'color': 'white', 'size': 16}},
        number = {'font': {'color': 'white', 'size': 20}},
        gauge = {
            'axis': {'range': [None, max_value], 'tickcolor': 'white', 'tickfont': {'color': 'white'}},
            'bar': {'color': color},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "white",
            'steps': [
                {'range': [0, 80], 'color': "rgba(0, 255, 136, 0.3)"},
                {'range': [80, 92], 'color': "rgba(255, 183, 0, 0.3)"},
                {'range': [92, 100], 'color': "rgba(255, 0, 110, 0.3)"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        height=250,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def get_available_log_content(instance_id: str):
    """
    Get available.log content from CloudWatch Logs for SAP availability monitoring.
    Returns the raw log content or None if not available.
    """
    try:
        # Get CloudWatch Logs client
        logs_client = get_cross_account_boto3_client_cached('logs')
        if not logs_client:
            return None
        
        # Get instance details to get the instance name
        details = get_instance_details(instance_id)
        if not details:
            return None
        
        instance_name = next((tag['Value'] for tag in details.get('Tags', []) if tag['Key'] == 'Name'), '')
        
        # Determine environment based on instance name patterns
        is_production = any(prod_pattern in instance_name.upper() 
                          for prod_pattern in ['PRD', 'PROD', 'PRODUCTION'])
        
        # CloudWatch Log Groups for SAP availability monitoring
        if is_production:
            possible_log_groups = [
                '/aws/lambda/sap-availability-heartbeat-prod',
                '/aws/lambda/sap-availability-prod'
            ]
        else:
            possible_log_groups = [
                '/aws/lambda/sap-availability-heartbeat-qa',
                '/aws/lambda/sap-availability-qa',
                '/aws/lambda/sap-availability-heartbeat-dev',
                '/aws/lambda/sap-availability-dev'
            ]
        
        # Try each log group to find available.log content
        for log_group_name in possible_log_groups:
            try:
                # Get recent log streams
                streams_response = logs_client.describe_log_streams(
                    logGroupName=log_group_name,
                    orderBy='LastEventTime',
                    descending=True,
                    limit=10
                )
                
                # Search through recent log streams for available.log content
                for stream in streams_response.get('logStreams', []):
                    events_response = logs_client.get_log_events(
                        logGroupName=log_group_name,
                        logStreamName=stream['logStreamName'],
                        limit=100
                    )
                    
                    # Look for available.log content in log events
                    for event in events_response.get('events', []):
                        message = event.get('message', '')
                        
                        # Check if this log event contains available.log content for our server
                        if ('available.log' in message.lower() and 
                            instance_name.lower() in message.lower()):
                            return message
                            
            except Exception as e:
                # Continue to next log group if this one fails
                continue
        
        return None
        
    except Exception as e:
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Error getting available.log content: {e}\n")
        return None

def get_sap_availability_data(instance_id: str):
    """
    Get SAP availability data from CloudWatch Logs.
    The data is extracted by a Lambda function and stored in CloudWatch Logs.
    
    Returns a list of SAP services with their availability status.
    """
    try:
        # Get CloudWatch Logs client
        logs_client = get_cross_account_boto3_client_cached('logs')
        if not logs_client:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Failed to get CloudWatch Logs client\n")
            return []
        
        # Get instance details to get the instance name
        details = get_instance_details(instance_id)
        if not details:
            return []
        
        instance_name = next((tag['Value'] for tag in details.get('Tags', []) if tag['Key'] == 'Name'), '')
        
        # Determine environment based on instance name patterns
        # Production instances typically have 'PRD' in their names
        is_production = any(prod_pattern in instance_name.upper() 
                          for prod_pattern in ['PRD', 'PROD', 'PRODUCTION'])
        
        # CloudWatch Log Groups for SAP availability monitoring
        if is_production:
            possible_log_groups = [
                '/aws/lambda/sap-availability-heartbeat-prod',
                '/aws/lambda/sap-availability-heartbeat-prod-b'
            ]
        else:
            # QA/DEV environments
            possible_log_groups = [
                '/aws/lambda/sap-availability-heartbeat',
                '/aws/lambda/sap-availability-heartbeat-b'
            ]
        
        sap_services = []
        
        # Query CloudWatch Logs for SAP availability data
        for log_group in possible_log_groups:
            try:
                # Query logs for the last 24 hours
                end_time = int(time.time() * 1000)
                start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago
                
                # Search for FILE_CHECK_DETAIL logs containing this instance_id
                query = f'''
                fields @timestamp, @message
                | filter @message like /FILE_CHECK_DETAIL/
                | filter @message like /{instance_id}/
                | sort @timestamp desc
                | limit 20
                '''
                
                response = logs_client.start_query(
                    logGroupName=log_group,
                    startTime=start_time,
                    endTime=end_time,
                    queryString=query
                )
                
                query_id = response['queryId']
                
                # Wait for query to complete
                import time as time_module
                time_module.sleep(2)  # Give query time to execute
                
                results_response = logs_client.get_query_results(queryId=query_id)
                
                if results_response['status'] == 'Complete' and results_response['results']:
                    # Parse the log results
                    parsed_services = parse_sap_log_results(results_response['results'], instance_id)
                    sap_services.extend(parsed_services)
                    
                    with open("/tmp/streamlit_aws_debug.log", "a") as f:
                        f.write(f"[{time.ctime()}] Found {len(parsed_services)} SAP services in {log_group} for {instance_name}\n")
                
            except Exception as log_group_error:
                # Log group might not exist, continue to next one
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] Log group {log_group} not accessible: {str(log_group_error)}\n")
                continue
        
        # If no real data found, return placeholder data for demo
        if not sap_services:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] No SAP data found in CloudWatch Logs for {instance_name}, using placeholder data\n")
            
            # Return placeholder data based on instance name patterns
            return get_placeholder_sap_data(instance_name)
        
        return sap_services
        
    except Exception as e:
        with open("/tmp/streamlit_aws_debug.log", "a") as f:
            f.write(f"[{time.ctime()}] Error getting SAP availability data from CloudWatch Logs: {str(e)}\n")
        return []

def parse_sap_log_results(log_results, instance_id):
    """
    Parse CloudWatch Logs results to extract SAP availability data.
    
    Expected log format from Lambda:
    FILE_CHECK_DETAIL: {"vm_name": "...", "instance_id": "...", "file_path": "...", 
                      "status": "AVAILABLE/UNAVAILABLE", "details": "...", 
                      "raw_output": "...", "timestamp": "...", "environment": "..."}
    """
    import json
    import re
    services = {}
    
    for result in log_results:
        try:
            # Extract message from CloudWatch Logs result
            message = ""
            log_timestamp = ""
            
            for field in result:
                if field['field'] == '@message':
                    message = field['value']
                elif field['field'] == '@timestamp':
                    log_timestamp = field['value']
            
            if not message or 'FILE_CHECK_DETAIL:' not in message:
                continue
            
            # Extract JSON from the FILE_CHECK_DETAIL log line
            # Pattern: FILE_CHECK_DETAIL: {"vm_name": ...}
            json_start = message.find('{')
            if json_start == -1:
                continue
                
            json_str = message[json_start:]
            
            # Parse the JSON data
            try:
                sap_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common JSON issues (double quotes inside strings)
                json_str = json_str.replace('""', '"')
                try:
                    sap_data = json.loads(json_str)
                except json.JSONDecodeError:
                    continue
            
            # Validate that this is for the correct instance
            if sap_data.get('instance_id') != instance_id:
                continue
            
            # Extract service information from file path
            file_path = sap_data.get('file_path', '')
            # Example: /usr/sap/DAA/SMDA98/work/available.log -> DAA/SMDA98
            path_match = re.search(r'/usr/sap/([^/]+)/([^/]+)/', file_path)
            if path_match:
                sap_system = path_match.group(1)
                instance_num = path_match.group(2)
                service_name = f"{sap_system} {instance_num}"
            else:
                service_name = "Unknown SAP Service"
            
            status = sap_data.get('status', 'UNKNOWN')
            raw_output = sap_data.get('raw_output', '')
            details = sap_data.get('details', '')
            timestamp = sap_data.get('timestamp', log_timestamp)
            environment = sap_data.get('environment', 'UNKNOWN')
            vm_name = sap_data.get('vm_name', 'Unknown')
            
            # Create unique service key
            service_key = f"{vm_name}_{service_name}"
            
            # Only keep the most recent status for each service
            if service_key not in services or timestamp > services[service_key].get('timestamp', ''):
                services[service_key] = {
                    'path': file_path,
                    'service': service_name,
                    'instance': vm_name,
                    'status': status,
                    'details': details,
                    'raw_output': raw_output,
                    'timestamp': timestamp,
                    'environment': environment,
                    'history': [{
                        'status': status,
                        'timestamp': timestamp,
                        'raw_output': raw_output
                    }]
                }
            
        except Exception as parse_error:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Error parsing log result: {str(parse_error)}\n")
            continue
    
    return list(services.values())

def get_placeholder_sap_data(instance_name):
    """Fallback placeholder data when no CloudWatch logs are found"""
    sap_services = []
    
    # Generate placeholder data based on instance name patterns
    if 'ERP' in instance_name.upper():
        sap_services.append({
            'path': '/usr/sap/ERP/DVEBMGS00/work/available.log',
            'service': 'SAP ERP',
            'instance': 'DVEBMGS00',
            'history': [
                {'status': 'AVAILABLE', 'start_time': '2025-09-14 08:00:00', 'end_time': '2025-09-14 23:59:59'},
                {'status': 'UNAVAILABLE', 'start_time': '2025-09-14 02:00:00', 'end_time': '2025-09-14 02:15:00'},
            ]
        })
    
    if 'CRM' in instance_name.upper():
        sap_services.append({
            'path': '/usr/sap/CRM/DVEBMGS01/work/available.log',
            'service': 'SAP CRM',
            'instance': 'DVEBMGS01',
            'history': [
                {'status': 'AVAILABLE', 'start_time': '2025-09-14 00:00:00', 'end_time': '2025-09-14 23:59:59'},
            ]
        })
    
    return sap_services

def create_sap_availability_table(sap_data):
    """Create a table showing SAP availability data"""
    if not sap_data:
        return st.info("No se encontraron servicios SAP para esta instancia.")
    
    st.markdown("## 🔧 Disponibilidad Servicios SAP")
    
    for service in sap_data:
        st.markdown(f"### {service['service']} ({service['instance']})")
        st.markdown(f"**Path:** `{service['path']}`")
        
        # Get current status from the service data
        current_status = service.get('status', 'UNKNOWN')
        status_color = "🟢" if current_status == 'AVAILABLE' else "🔴" if current_status == 'UNAVAILABLE' else "⚫"
        st.markdown(f"**Estado Actual:** {status_color} {current_status}")
        
        # Show additional details if available
        if service.get('details'):
            st.markdown(f"**Detalles:** {service['details']}")
        
        # Show raw output from SAP logs
        if service.get('raw_output'):
            with st.expander("Ver salida completa del log"):
                st.code(service['raw_output'])
        
        # Show environment and timestamp
        if service.get('environment'):
            st.markdown(f"**Ambiente:** {service['environment']}")
        
        if service.get('timestamp'):
            st.markdown(f"**Última verificación:** {service['timestamp']}")
        
        # Create DataFrame for history if available
        if service.get('history'):
            df_data = []
            for i, entry in enumerate(service['history'][:10]):  # Show max 10 entries
                df_data.append({
                    '#': i + 1,
                    'Estado': '🟢 DISPONIBLE' if entry['status'] == 'AVAILABLE' else '🔴 NO DISPONIBLE',
                    'Timestamp': entry.get('timestamp', 'N/A'),
                    'Salida': entry.get('raw_output', 'N/A')[:50] + '...' if len(entry.get('raw_output', '')) > 50 else entry.get('raw_output', 'N/A')
                })
            
            if df_data:
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de historial disponibles")
        
        st.markdown("---")

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
                alarm_name = alarm.get('AlarmName', '')
                
                # Check if this is a preventive alarm
                if state == "ALARM" and ('ALERTA' in alarm_name.upper() or 'PROACTIVA' in alarm_name.upper()):
                    color = "yellow"
                else:
                    color = "red" if state == "ALARM" else "gray" if state == "INSUFFICIENT_DATA" else "green"
                
                alarm_arn = alarm.get('AlarmArn')
                st.markdown(create_alarm_item_html(alarm_name, color, alarm_arn), unsafe_allow_html=True)
        else:
            st.info("No se encontraron alarmas para esta instancia.")
    with col2:
        # SAP Availability Section
        sap_data = get_sap_availability_data(instance_id)
        if sap_data:
            create_sap_availability_table(sap_data)
            st.markdown("---")
        
        # Available.log Content Section
        st.markdown("## 📋 Contenido de available.log")
        log_content = get_available_log_content(instance_id)
        if log_content:
            # Display the log content in an expandable section
            with st.expander("📄 Ver contenido completo del archivo available.log", expanded=False):
                st.code(log_content, language="text")
        else:
            st.info("❌ NO existe available.log para este servidor.")
        
        st.markdown("---")
        st.markdown("## 📊 Métricas de Rendimiento")
        
        # Create columns for gauges
        gauge_col1, gauge_col2 = st.columns(2)
        
        # CPU Metric
        with gauge_col1:
            cpu_datapoint = get_cpu_utilization(instance_id)
            if cpu_datapoint:
                cpu_avg = round(cpu_datapoint.get('Average', 0), 2)
                cpu_fig = create_gauge(cpu_avg, "🖥️ CPU %", 100)
                st.plotly_chart(cpu_fig, use_container_width=True)
            else:
                st.info("No hay datos de CPU disponibles.")
        
        # Memory Metric
        with gauge_col2:
            memory_datapoint = get_memory_utilization(instance_id)
            if memory_datapoint:
                mem_avg = round(memory_datapoint.get('Average', 0), 2)
                mem_fig = create_gauge(mem_avg, "🧠 RAM %", 100)
                st.plotly_chart(mem_fig, use_container_width=True)
            else:
                st.info("No hay datos de memoria disponibles.")
        
        # Disk Metrics
        st.markdown("---")
        st.markdown("**💾 Utilización de Discos**")
        disk_metrics = get_disk_utilization(instance_id)
        if disk_metrics:
            # Create columns for disk gauges (2 per row)
            disk_cols = st.columns(2)
            for i, disk in enumerate(disk_metrics):
                device = disk['device']
                usage = round(disk['usage'], 2)
                
                with disk_cols[i % 2]:
                    disk_fig = create_gauge(usage, f"💾 {device}", 100)
                    st.plotly_chart(disk_fig, use_container_width=True)
        else:
            st.info("No hay datos de disco disponibles.")

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
    preventive = alerts_data.get('PREVENTIVE', 0)
    insufficient = alerts_data.get('INSUFFICIENT_DATA', 0) + alerts_data.get('UNKNOWN', 0)  # Treat UNKNOWN as INSUFFICIENT_DATA
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

def create_server_card(instance: dict):
    vm_name = instance.get('Name', instance.get('ID', 'N/A'))
    instance_id = instance.get('ID', '')
    private_ip = instance.get('PrivateIP', 'N/A')
    state = instance.get('State', 'unknown')
    alerts = instance.get('Alarms', Counter())
    
    # Determine card color based on alarms
    if alerts.get('ALARM', 0) > 0:
        card_status = 'red'
    elif alerts.get('PREVENTIVE', 0) > 0:
        card_status = 'yellow'
    elif alerts.get('INSUFFICIENT_DATA', 0) > 0 or alerts.get('UNKNOWN', 0) > 0:
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
    has_preventive = False
    has_insufficient = False
    
    for instance in instances:
        alerts = instance.get('Alarms', Counter())
        if alerts.get('ALARM', 0) > 0:
            has_critical = True
            break
        elif alerts.get('PREVENTIVE', 0) > 0:
            has_preventive = True
        elif alerts.get('INSUFFICIENT_DATA', 0) > 0 or alerts.get('UNKNOWN', 0) > 0:
            has_insufficient = True
    
    # Set group color based on worst status
    if has_critical:
        group_status = 'red'
    elif has_preventive:
        group_status = 'yellow'
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