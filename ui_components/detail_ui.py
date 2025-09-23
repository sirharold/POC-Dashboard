"""
Detail page UI Components that preserve the exact original detail page behavior.
"""
import streamlit as st
import datetime
import plotly.graph_objects as go
import pandas as pd
from utils.helpers import create_alarm_item_html, create_alarm_legend


class DetailUI:
    """Manages detail page UI components, preserving original appearance and behavior."""
    
    def __init__(self, aws_service):
        """Initialize with AWS service dependency."""
        self.aws_service = aws_service

    def get_cpu_utilization(self, instance_id: str):
        """Get CPU utilization. Same as original function."""
        try:
            cloudwatch = self.aws_service.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch: return None
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2', MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
                EndTime=datetime.datetime.utcnow(), Period=300, Statistics=['Average']
            )
            return sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0] if response['Datapoints'] else None
        except Exception:
            return None

    def get_memory_utilization(self, instance_id: str):
        """Get memory utilization. Same as original function."""
        try:
            cloudwatch = self.aws_service.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch: return None
            # Try CWAgent namespace first
            response = cloudwatch.get_metric_statistics(
                Namespace='CWAgent', MetricName='mem_used_percent',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
                EndTime=datetime.datetime.utcnow(), Period=300, Statistics=['Average']
            )
            return sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0] if response['Datapoints'] else None
        except Exception:
            return None

    def get_disk_utilization(self, instance_id: str):
        """Get disk utilization. Same as original function."""
        try:
            cloudwatch = self.aws_service.get_cross_account_boto3_client('cloudwatch')
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
        except Exception:
            return []

    def create_gauge(self, value, title, max_value=100):
        """Create a gauge chart using plotly. Same as original function."""
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

    def display_detail_page(self, instance_id: str):
        """Display detail page. Exact same logic as original function."""
        details = self.aws_service.get_instance_details(instance_id)
        # Preserve columns parameter when returning to dashboard
        columns_param = st.query_params.get('columns', '2')
        if st.button("← Volver al Dashboard", type="secondary"):
            # Clear detail query param and preserve columns
            st.query_params.clear()
            st.query_params.update({"columns": columns_param})
            st.rerun()
        if not details:
            st.error(f"No se pudieron obtener los detalles para la instancia con ID: {instance_id}")
            return
        instance_name = next((tag['Value'] for tag in details.get('Tags', []) if tag['Key'] == 'Name'), instance_id)
        st.markdown(f"<h1 style='margin: 0; padding: 0;'>Detalles de <span style='color: #00d4ff;'>{instance_name}</span></h1>", unsafe_allow_html=True)
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
            alarms = self.aws_service.get_alarms_for_instance(instance_id)
            if alarms:
                for alarm in alarms:
                    state = alarm.get('StateValue')
                    alarm_name = alarm.get('AlarmName', '')
                    
                    # Check if this is a preventive alarm
                    if state == "ALARM" and ('ALERTA' in alarm_name.upper() or 'PROACTIVA' in alarm_name.upper() or 'PREVENTIVA' in alarm_name.upper()):
                        color = "yellow"
                    else:
                        color = "red" if state == "ALARM" else "gray" if state == "INSUFFICIENT_DATA" else "green"
                    
                    alarm_arn = alarm.get('AlarmArn')
                    st.markdown(create_alarm_item_html(alarm_name, color, alarm_arn), unsafe_allow_html=True)
            else:
                st.info("No se encontraron alarmas para esta instancia.")
        with col2:
            # SAP Availability Section
            from services.sap_service import SAPService
            sap_service = SAPService(self.aws_service)
            sap_data = sap_service.get_sap_availability_data(instance_id)
            if sap_data:
                sap_service.create_sap_availability_table(sap_data)
                st.markdown("---")
            
            # Available.log Content Section
            st.markdown("## 📋 Contenido de available.log")
            log_content = sap_service.get_available_log_content(instance_id)
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
                cpu_datapoint = self.get_cpu_utilization(instance_id)
                if cpu_datapoint:
                    cpu_avg = round(cpu_datapoint.get('Average', 0), 2)
                    cpu_fig = self.create_gauge(cpu_avg, "🖥️ CPU %", 100)
                    st.plotly_chart(cpu_fig, use_container_width=True)
                else:
                    st.info("No hay datos de CPU disponibles.")
            
            # Memory Metric
            with gauge_col2:
                memory_datapoint = self.get_memory_utilization(instance_id)
                if memory_datapoint:
                    mem_avg = round(memory_datapoint.get('Average', 0), 2)
                    mem_fig = self.create_gauge(mem_avg, "🧠 RAM %", 100)
                    st.plotly_chart(mem_fig, use_container_width=True)
                else:
                    st.info("No hay datos de memoria disponibles.")
            
            # Disk Metrics
            st.markdown("---")
            st.markdown("**💾 Utilización de Discos**")
            disk_metrics = self.get_disk_utilization(instance_id)
            if disk_metrics:
                # Create columns for disk gauges (2 per row)
                disk_cols = st.columns(2)
                for i, disk in enumerate(disk_metrics):
                    device = disk['device']
                    usage = round(disk['usage'], 2)
                    
                    with disk_cols[i % 2]:
                        disk_fig = self.create_gauge(usage, f"💾 {device}", 100)
                        st.plotly_chart(disk_fig, use_container_width=True)
            else:
                st.info("No hay datos de disco disponibles.")