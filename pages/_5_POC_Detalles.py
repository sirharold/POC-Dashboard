
"""
Real-Time AWS EC2 Instance Detail Page (Boto3 Version)
"""
import streamlit as st
import boto3
import datetime
from botocore.exceptions import ClientError
from utils.helpers import load_css, create_alarm_item_html

# ========================================================================
# STREAMLIT CONFIGURATION
# ========================================================================
st.set_page_config(
    page_title="Detalles del Servidor (POC)",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========================================================================
# DATA FETCHING FROM AWS (BOTO3)
# ========================================================================

@st.cache_data(ttl=60)
def get_instance_details(instance_id: str):
    """Fetches detailed information for a single EC2 instance using boto3."""
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if response['Reservations'] and response['Reservations'][0]['Instances']:
            return response['Reservations'][0]['Instances'][0]
        return None
    except (ClientError, IndexError):
        return None

@st.cache_data(ttl=60)
def get_alarms_for_instance(instance_id: str):
    """Fetches all CloudWatch alarms for a specific instance using boto3."""
    try:
        cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
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
    """Fetches the most recent CPUUtilization metric from CloudWatch using boto3."""
    try:
        cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
            EndTime=datetime.datetime.utcnow(),
            Period=300,
            Statistics=['Average']
        )
        return sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0] if response['Datapoints'] else None
    except ClientError:
        return None

@st.cache_data(ttl=60)
def get_memory_utilization(instance_id: str):
    """Fetches the most recent memory utilization metric from the CloudWatch Agent."""
    try:
        cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        response = cloudwatch.get_metric_statistics(
            Namespace='CWAgent',
            MetricName='mem_used_percent',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
            EndTime=datetime.datetime.utcnow(),
            Period=300,
            Statistics=['Average']
        )
        return sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0] if response['Datapoints'] else None
    except ClientError:
        return None

@st.cache_data(ttl=60)
def get_disk_utilization(instance_id: str):
    """Fetches the most recent disk utilization metric for the root path ('/')."""
    try:
        cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        response = cloudwatch.get_metric_statistics(
            Namespace='CWAgent',
            MetricName='disk_used_percent',
            Dimensions=[
                {'Name': 'InstanceId', 'Value': instance_id},
                {'Name': 'path', 'Value': '/'}
            ],
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
            EndTime=datetime.datetime.utcnow(),
            Period=300,
            Statistics=['Average']
        )
        return sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0] if response['Datapoints'] else None
    except ClientError:
        return None

# ========================================================================
# UI RENDERING
# ========================================================================

def display_page(instance_id: str):
    """Renders the entire detail page for the given instance ID."""
    details = get_instance_details(instance_id)
    if not details:
        st.error(f"No se pudieron obtener los detalles para la instancia con ID: {instance_id}")
        return

    instance_name = next((tag['Value'] for tag in details.get('Tags', []) if tag['Key'] == 'Name'), instance_id)
    
    st.markdown(f"<h1>Detalles de <span style='color: #00d4ff;'>{instance_name}</span></h1>", unsafe_allow_html=True)
    st.page_link("pages/POC_AWS_Alive.py", label="← Volver al Dashboard POC", icon="☁️")
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
        alarms = get_alarms_for_instance(instance_id)
        if alarms:
            for alarm in alarms:
                state = alarm.get('StateValue')
                color = "red" if state == "ALARM" else "yellow" if state == "INSUFFICIENT_DATA" else "green"
                st.markdown(create_alarm_item_html(alarm.get('AlarmName'), color), unsafe_allow_html=True)
        else:
            st.info("No se encontraron alarmas para esta instancia.")

    with col2:
        st.markdown("## 📊 Métricas de Rendimiento")
        
        # --- CPU --- 
        cpu_datapoint = get_cpu_utilization(instance_id)
        if cpu_datapoint:
            cpu_avg = round(cpu_datapoint.get('Average', 0), 2)
            st.markdown("**🖥️ Utilización de CPU (promedio 5 min)**")
            st.progress(cpu_avg / 100, f"{cpu_avg}%")
        else:
            st.info("No hay datos de CPU (AWS/EC2) disponibles.")

        # --- Memory --- 
        mem_datapoint = get_memory_utilization(instance_id)
        if mem_datapoint:
            mem_avg = round(mem_datapoint.get('Average', 0), 2)
            st.markdown("**🧠 Uso de Memoria (promedio 5 min)**")
            st.progress(mem_avg / 100, f"{mem_avg}%")

        # --- Disk --- 
        disk_datapoint = get_disk_utilization(instance_id)
        if disk_datapoint:
            disk_avg = round(disk_datapoint.get('Average', 0), 2)
            st.markdown("**💿 Uso de Disco '/' (promedio 5 min)**")
            st.progress(disk_avg / 100, f"{disk_avg}%")
        
        st.divider()

        # --- Conditional Warning --- 
        if not mem_datapoint or not disk_datapoint:
            st.warning("**Nota sobre Métricas Adicionales:**")
            st.info("""
            Para visualizar el uso de **Memoria RAM** y/o **Disco**, el [Agente de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html) debe estar instalado y configurado en la instancia para enviar estas métricas al namespace `CWAgent`.
            - Si una métrica no aparece, es porque no se encontraron datos para ella.
            """)

# ========================================================================
# MAIN LOGIC
# ========================================================================

load_css()

if 'poc_vm_id' in st.session_state and st.session_state.poc_vm_id:
    display_page(st.session_state.poc_vm_id)
else:
    st.error("No se ha seleccionado ninguna instancia.")
    st.info("Por favor, regrese al dashboard del POC y seleccione un servidor.")
    st.page_link("pages/POC_AWS_Alive.py", label="← Volver al Dashboard POC", icon="☁️")
