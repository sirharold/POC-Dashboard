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
        """Get memory utilization for both Linux and Windows systems."""
        try:
            cloudwatch = self.aws_service.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch: return None
            
            # Try different memory metrics for Linux and Windows
            memory_metrics = [
                # Linux CloudWatch Agent
                {'Namespace': 'CWAgent', 'MetricName': 'mem_used_percent', 'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]},
                # Windows CloudWatch Agent - various possible names
                {'Namespace': 'CWAgent', 'MetricName': 'Memory % Committed Bytes In Use', 'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]},
                {'Namespace': 'CWAgent', 'MetricName': 'Memory Available Bytes', 'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]},
                # Windows Performance Counters
                {'Namespace': 'AWS/EC2', 'MetricName': 'MemoryUtilization', 'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]},
            ]
            
            for metric in memory_metrics:
                try:
                    response = cloudwatch.get_metric_statistics(
                        Namespace=metric['Namespace'],
                        MetricName=metric['MetricName'],
                        Dimensions=metric['Dimensions'],
                        StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
                        EndTime=datetime.datetime.utcnow(),
                        Period=300,
                        Statistics=['Average']
                    )
                    if response['Datapoints']:
                        datapoint = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0]
                        # For Memory Available Bytes, convert to percentage (assuming 8GB total for estimate)
                        if metric['MetricName'] == 'Memory Available Bytes':
                            available_gb = datapoint['Average'] / (1024**3)  # Convert to GB
                            estimated_total_gb = 8  # Default estimate, could be improved
                            datapoint['Average'] = max(0, 100 - (available_gb / estimated_total_gb * 100))
                        return datapoint
                except Exception:
                    continue
            
            return None
        except Exception:
            return None

    def get_disk_utilization(self, instance_id: str):
        """Get disk utilization for both Linux and Windows systems."""
        try:
            cloudwatch = self.aws_service.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch: return []
            
            disk_metrics = []
            
            # Try different disk metrics for Linux and Windows
            disk_metric_names = [
                'disk_used_percent',        # Linux CWAgent
                'LogicalDisk % Free Space', # Windows CWAgent
            ]
            
            paginator = cloudwatch.get_paginator('list_metrics')
            
            for metric_name in disk_metric_names:
                try:
                    pages = paginator.paginate(
                        Namespace='CWAgent',
                        MetricName=metric_name,
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
                    )
                    
                    for page in pages:
                        for metric in page['Metrics']:
                            # Get the device/path/objectname dimension
                            instance_dim = None # For Windows drive letters
                            
                            for dim in metric['Dimensions']:
                                if dim['Name'] == 'device':
                                    device = dim['Value']
                                elif dim['Name'] == 'path':
                                    path = dim['Value']
                                elif dim['Name'] == 'objectname':
                                    objectname = dim['Value']
                                elif dim['Name'] == 'instance': # This dimension often holds the drive letter
                                    instance_dim = dim['Value']
                            
                            # Determine disk name based on OS type
                            if objectname == 'LogicalDisk' and instance_dim:  # Windows
                                disk_name = instance_dim
                                if any(exclude in disk_name.lower() for exclude in ['_total', 'system', 'harddisk']):
                                    continue
                            else:  # Linux
                                disk_name = device or path or 'Unknown'
                                if any(exclude in disk_name.lower() for exclude in ['tmpfs', 'devtmpfs', 'udev', 'proc', 'sys', 'run']):
                                    continue
                            
                            if disk_name:
                                # Get the latest value
                                response = cloudwatch.get_metric_statistics(
                                    Namespace='CWAgent',
                                    MetricName=metric_name,
                                    Dimensions=metric['Dimensions'],
                                    StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
                                    EndTime=datetime.datetime.utcnow(),
                                    Period=300,
                                    Statistics=['Average']
                                )
                                
                                if response['Datapoints']:
                                    latest = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0]
                                    usage_value = latest['Average']
                                    
                                    # Convert Windows "Free Space" to "Used Space"
                                    if metric_name == 'LogicalDisk % Free Space':
                                        usage_value = 100 - usage_value
                                    
                                    disk_metrics.append({
                                        'device': disk_name,
                                        'usage': usage_value,
                                        'dimensions': metric['Dimensions'] # Return all dimensions for debugging
                                    })
                    
                    # If we found metrics with this metric name, break to avoid duplicates
                    if disk_metrics:
                        break
                        
                except Exception:
                    continue
            
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

    def create_history_chart(self, df: pd.DataFrame, title: str, y_column: str, y_title: str) -> go.Figure:
        """Create a time-series line chart for a given metric."""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['Timestamp'], 
            y=df[y_column],
            mode='lines', 
            line=dict(color='#00d4ff', width=2),
            fill='tozeroy', # Fill area under the line
            fillcolor='rgba(0, 212, 255, 0.1)'
        ))

        fig.update_layout(
            title={
                'text': title,
                'y':0.9,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'white', 'size': 16}
            },
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0.1)",
            font_color="white",
            height=300,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis_title="",
            yaxis_title=y_title,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='rgba(255, 255, 255, 0.1)')
        )
        return fig

    def _is_disk_alarm(self, alarm_name: str) -> bool:
        """Check if an alarm is disk-related by its name."""
        disk_keywords = ['DISK', 'DISCO', 'STORAGE', 'FILESYSTEM', 'VOLUME']
        return any(kw in alarm_name.upper() for kw in disk_keywords)

    def _display_sap_service_alarms(self, alarms: list):
        """Displays a dedicated UI component for specific SAP service alarms."""
        st.markdown("## ✳️ Estado Servicios SAP")

        sap_alarm_keywords = [
            "SAP JAVA CENTRAL DOWN",
            "SAP ABAP CENTRAL DOWN",
            "SAP ABAP DOW", # Typo from user request, kept for matching
            "SAP JAVA DOWN",
            "SAP SERVICES"
        ]

        # Find the relevant alarms
        sap_alarms = []
        for keyword in sap_alarm_keywords:
            found_alarm = next((alarm for alarm in alarms if keyword in alarm.get('AlarmName', '').upper()), None)
            sap_alarms.append((keyword, found_alarm))

        if not any(alarm for _, alarm in sap_alarms):
            st.info("No se encontraron alarmas específicas de servicios SAP para esta instancia.")
            return

        # Create a styled container for the statuses
        st.markdown("""<div style='background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 16px; backdrop-filter: blur(10px);'>""", unsafe_allow_html=True)
        
        for keyword, alarm in sap_alarms:
            if alarm:
                state = alarm.get('StateValue', 'UNKNOWN')
                if state == 'ALARM':
                    status_icon = "<span style='color: #ff006e; font-size: 1.5rem;'>●</span>"
                    status_text = "<span style='color: #ff006e;'>DOWN</span>"
                else:
                    status_icon = "<span style='color: #00ff88; font-size: 1.5rem;'>●</span>"
                    status_text = "OK"
            else:
                status_icon = "<span style='color: #808080; font-size: 1.5rem;'>●</span>"
                status_text = "N/A"

            # Clean up keyword for display
            display_name = keyword.replace("SAP", "").replace("DOWN", "").replace("INCIDENTE", "").strip()

            st.markdown(f"""<div style='display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05);'>
                <span style='font-weight: 600;'>{display_name}</span>
                <div style='display: flex; align-items: center; gap: 8px;'>
                    {status_icon} {status_text}
                </div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

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
            st.text(f"S.O.: {details.get('PlatformDetails', 'Linux/UNIX')}")

            with st.expander("⚙️ Metadatos de la Instancia"):
                st.text(f"AMI ID: {details.get('ImageId')}")
                # Format launch time for readability
                launch_time = details.get('LaunchTime')
                if launch_time:
                    st.text(f"Lanzamiento: {launch_time.strftime('%Y-%m-%d %H:%M:%S')}")
                st.text(f"VPC ID: {details.get('VpcId')}")
                st.text(f"Subnet ID: {details.get('SubnetId')}")
            
            # Display Security Groups in a separate expander
            sgs = details.get('SecurityGroups', [])
            with st.expander(f"🔒 Grupos de Seguridad ({len(sgs)})"):
                if sgs:
                    for sg in sgs:
                        st.text(f"- {sg['GroupName']} ({sg['GroupId']})")
                else:
                    st.text("No hay grupos de seguridad asociados.")

            # --- SAP Service Status ---
            self._display_sap_service_alarms(alarms)

            st.markdown("## 🚨 Alarmas Generales")
            st.markdown(create_alarm_legend(), unsafe_allow_html=True)
            
            if alarms:
                # --- Advanced Alarm Categorization ---
                proactiva_disk_alarms = []
                alerta_disk_alarms = []
                unassociated_disk_alarms = []
                other_alarms = []
                
                block_devices = details.get('BlockDeviceMappings', [])
                known_volume_ids = {bd.get('Ebs', {}).get('VolumeId') for bd in block_devices}

                for alarm in alarms:
                    alarm_name_upper = alarm.get('AlarmName', '').upper()

                    # Exclude SAP alarms from general categorization
                    if 'INCIDENTE SAP' in alarm_name_upper:
                        continue

                    # Category 1: Named PROACTIVA-DISK
                    if 'PROACTIVA-DISK' in alarm_name_upper:
                        proactiva_disk_alarms.append(alarm)
                        continue
                    
                    # Category 2: Named ALERTA-DISK
                    if 'ALERTA-DISK' in alarm_name_upper:
                        alerta_disk_alarms.append(alarm)
                        continue

                    # Category 3: Unassociated Disk Alarms
                    if self._is_disk_alarm(alarm_name_upper):
                        is_associated = False
                        for dim in alarm.get('Dimensions', []):
                            if dim.get('Name') == 'VolumeId' and dim.get('Value') in known_volume_ids:
                                is_associated = True
                                break
                        if not is_associated:
                            unassociated_disk_alarms.append(alarm)
                        else:
                            other_alarms.append(alarm) # Is a disk alarm, but associated and not named
                    else:
                        # Category 4: All other alarms
                        other_alarms.append(alarm)

                # --- Render Categorized Alarms ---
                with st.expander(f"🟡 Alarmas PROACTIVA-DISK ({len(proactiva_disk_alarms)})"):
                    if proactiva_disk_alarms:
                        for alarm in proactiva_disk_alarms:
                            st.markdown(create_alarm_item_html(alarm.get('AlarmName'), "yellow"), unsafe_allow_html=True)
                    else:
                        st.text("No hay alarmas de este tipo.")

                with st.expander(f"🟡 Alarmas ALERTA-DISK ({len(alerta_disk_alarms)})"):
                    if alerta_disk_alarms:
                        for alarm in alerta_disk_alarms:
                            st.markdown(create_alarm_item_html(alarm.get('AlarmName'), "yellow"), unsafe_allow_html=True)
                    else:
                        st.text("No hay alarmas de este tipo.")
                
                with st.expander(f"❓ Alarmas de Disco No Asociado ({len(unassociated_disk_alarms)})"):
                    if unassociated_disk_alarms:
                        for alarm in unassociated_disk_alarms:
                            st.markdown(create_alarm_item_html(alarm.get('AlarmName'), "yellow"), unsafe_allow_html=True)
                    else:
                        st.text("No hay alarmas de este tipo.")

                # Render other alarms
                if other_alarms:
                    st.markdown("--- ") # Separator
                    for alarm in other_alarms:
                        state = alarm.get('StateValue')
                        alarm_name = alarm.get('AlarmName', '')
                        color = "red" if state == "ALARM" else "gray" if state == "INSUFFICIENT_DATA" else "green"
                        st.markdown(create_alarm_item_html(alarm_name, color), unsafe_allow_html=True)
            else:
                st.info("No se encontraron alarmas para esta instancia.")
        with col2:
            
            
            st.markdown("---")
            st.markdown("## 📊 Métricas de Rendimiento (Últimas 3 Horas)")

            # --- CPU History Chart ---
            cpu_df = self.aws_service.get_metric_history(instance_id, 'CPUUtilization', 'AWS/EC2')
            if not cpu_df.empty:
                cpu_chart = self.create_history_chart(cpu_df, "🖥️ Uso de CPU (%)", 'Average', 'Uso Promedio (%)')
                st.plotly_chart(cpu_chart, use_container_width=True)
            else:
                st.info("No hay datos históricos de CPU disponibles.")

            # --- Network History Chart ---
            st.markdown("### 🌐 Tráfico de Red")
            net_in_df = self.aws_service.get_metric_history(instance_id, 'NetworkIn', 'AWS/EC2', statistic='Sum')
            net_out_df = self.aws_service.get_metric_history(instance_id, 'NetworkOut', 'AWS/EC2', statistic='Sum')

            if not net_in_df.empty or not net_out_df.empty:
                net_fig = go.Figure()
                if not net_in_df.empty:
                    net_fig.add_trace(go.Scatter(x=net_in_df['Timestamp'], y=net_in_df['Sum'] / 1024**2, name='Entrada (MB)', line=dict(color='#00d4ff')))
                if not net_out_df.empty:
                    net_fig.add_trace(go.Scatter(x=net_out_df['Timestamp'], y=net_out_df['Sum'] / 1024**2, name='Salida (MB)', line=dict(color='#ffb700')))
                
                net_fig.update_layout(
                    title={'text': 'Tráfico de Red (MB)', 'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'color': 'white', 'size': 16}},
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0.1)", font_color="white", height=300,
                    margin=dict(l=20, r=20, t=50, b=20), yaxis_title="Megabytes (MB)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(net_fig, use_container_width=True)
            else:
                st.info("No hay datos históricos de red disponibles.")

            # --- Disk I/O History Chart ---
            st.markdown("**💾 Utilización de Discos**")

            # --- OS-Level Disk Usage ---
            st.markdown("##### Uso de Disco (Vista del Sistema Operativo)")
            disk_usage_metrics = self.get_disk_utilization(instance_id)
            if disk_usage_metrics:
                df_usage = pd.DataFrame(disk_usage_metrics)
                df_usage.rename(columns={'device': 'Unidad', 'usage': 'Uso %', 'dimensions': 'Dimensiones'}, inplace=True)
                df_usage['Uso %'] = df_usage['Uso %'].map('{:,.2f}%'.format)
                st.dataframe(df_usage[['Unidad', 'Uso %']], use_container_width=True)
            else:
                st.info("No se encontraron métricas de uso de disco desde el Agente de CloudWatch.")

            # --- AWS EBS Volume Details ---
            st.markdown("##### Volúmenes EBS (Vista de AWS)")
            block_devices = details.get('BlockDeviceMappings', [])
            volume_details = self.aws_service.get_volume_details(block_devices)
            if volume_details:
                aws_disk_data = []
                for mapping in block_devices:
                    vol_id = mapping.get('Ebs', {}).get('VolumeId')
                    if vol_id and vol_id in volume_details:
                        details = volume_details[vol_id]
                        aws_disk_data.append({
                            "Device AWS": mapping.get('DeviceName'),
                            "Tamaño (GB)": details.get('Size'),
                            "IOPS": details.get('Iops'),
                            "Tipo": details.get('VolumeType'),
                            "Tags": str(details.get('Tags', {}))
                        })
                df_vols = pd.DataFrame(aws_disk_data)
                # Sort by device name
                df_vols = df_vols.sort_values(by="Device AWS").reset_index(drop=True)
                st.dataframe(df_vols, use_container_width=True)
            else:
                st.info("No se encontraron volúmenes EBS para esta instancia.")

            # --- CloudWatch Log Viewer ---
            st.markdown("---")
            st.markdown("## 📜 Visor de Logs")
            log_groups = self.aws_service.get_log_groups(instance_id)

            if not log_groups:
                st.info("No se encontraron grupos de logs asociados a esta instancia.")
            else:
                selected_log_group = st.selectbox("Selecciona un grupo de logs para inspeccionar:", options=log_groups)
                if selected_log_group:
                    log_events = self.aws_service.get_log_events(selected_log_group)
                    if not log_events:
                        st.warning(f"No se encontraron eventos recientes en el grupo '{selected_log_group}'.")
                    else:
                        # Format logs for display
                        header = "Mostrando los últimos eventos...\n"
                        header += "------------------------------------\n"
                        
                        log_lines = []
                        for event in sorted(log_events, key=lambda x: x['timestamp'], reverse=True):
                            ts = datetime.datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            msg = event['message']
                            log_lines.append(f"[{ts}] {msg}")
                        
                        formatted_logs = header + "\n".join(log_lines)
                        st.code(formatted_logs, language='log')