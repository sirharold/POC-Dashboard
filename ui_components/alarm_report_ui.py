"""
Alarm Report UI component for displaying global alarm statistics.
"""
import streamlit as st
import pandas as pd
from typing import Dict, List
from collections import Counter
import re


class AlarmReportUI:
    """UI component for the global alarm report page."""
    
    def __init__(self, aws_service):
        """Initialize the alarm report UI with AWS service."""
        self.aws_service = aws_service
    
    def display_alarm_report(self):
        """Display the alarm report page."""
        # Add back to dashboard link
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("← Volver al Dashboard", type="secondary"):
                # Clear alarm_report query param to go back to dashboard
                st.query_params.clear()
                st.rerun()
        
        # Page title moved to header - removed duplicate
        
        # Environment selector - use same as dashboard
        ENVIRONMENTS = ["Production", "QA", "DEV"]
        if 'env_index' not in st.session_state:
            st.session_state.env_index = 0
        
        # Create columns for env selector and navigation
        col1, col2, col3 = st.columns([1, 6, 1])
        with col1:
            if st.button("←", use_container_width=True):
                st.session_state.env_index = (st.session_state.env_index - 1) % len(ENVIRONMENTS)
                st.rerun()
        with col3:
            if st.button("→", use_container_width=True):
                st.session_state.env_index = (st.session_state.env_index + 1) % len(ENVIRONMENTS)
                st.rerun()
        
        current_env = ENVIRONMENTS[st.session_state.env_index]
        with col2:
            st.markdown(f"<h3 style='text-align: center; margin: 0;'>Entorno: {current_env}</h3>", unsafe_allow_html=True)
        
        # Get all instance data with alarms
        instances_data = self.aws_service.get_aws_data()
        
        # Filter instances by the selected environment
        filtered_instances = [inst for inst in instances_data if inst.get('Environment') == current_env]
        
        # Process alarm data for report
        report_data = self._process_alarm_data(filtered_instances, current_env)
        
        # Create and display the report table
        if report_data:
            df = pd.DataFrame(report_data)

            # Add Theoretical Alarms Column
            df['total_alarms_theoretical'] = 2 + 1 + (df['disk_count'] * 3) + 1
            
            # Define column order and names
            column_order = [
                'instance_name', 'private_ip', 'instance_id',
                'cpu_alarms', 'ram_alarms', 'disk_alarms', 'disk_count',
                'ping_alarms', 'other_alarms',
                'insufficient_data', 'yellow_alarms', 'red_alarms',
                'total_alarms_theoretical', 'total_alarms'
            ]
            
            # Rename columns to Spanish
            column_names = {
                'instance_name': 'Nombre Instancia',
                'private_ip': 'IP Privada',
                'instance_id': 'Instance ID',
                'cpu_alarms': 'Alarmas CPU',
                'ram_alarms': 'Alarmas RAM',
                'disk_alarms': 'Alarmas Disco',
                'disk_count': 'Cant. Discos',
                'ping_alarms': 'Alarmas Ping',
                'other_alarms': 'Otras Alarmas',
                'insufficient_data': 'Datos Insuficientes',
                'yellow_alarms': 'Alarmas Amarillas',
                'red_alarms': 'Alarmas Rojas',
                'total_alarms_theoretical': 'T. A. Teóricas',
                'total_alarms': 'T. A. Actuales'
            }
            
            # Reorder and rename columns
            df = df[column_order]
            df.columns = [column_names[col] for col in column_order]

            # Sort by instance name by default
            df = df.sort_values(by='Nombre Instancia').reset_index(drop=True)

            # --- End of Setup ---

            # Display summary stats
            st.markdown("### 📈 Resumen")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("Total Instancias", len(df))
            with col2:
                st.metric("T. A. Teóricas", f"{df['T. A. Teóricas'].sum():.0f}")
            with col3:
                st.metric("T. A. Actuales", f"{df['T. A. Actuales'].sum():.0f}")
            with col4:
                st.metric("Alarmas Rojas", f"{df['Alarmas Rojas'].sum():.0f}")
            with col5:
                st.metric("Alarmas Amarillas", f"{df['Alarmas Amarillas'].sum():.0f}")
            with col6:
                st.metric("Datos Insuficientes", f"{df['Datos Insuficientes'].sum():.0f}")

            st.info("Se consideran alarmas amarillas las alarmas proactivas y de alerta. Las alarmas de disco deben ser 3x la cantidad de discos.")
            
            st.markdown("---")
            
            # Display the table
            st.markdown("### 📋 Detalle por Instancia")
            
            # Apply all styles and tooltips
            styled_df = df.style.apply(self._apply_row_highlight_styles, axis=1).apply(self._apply_validation_styles, axis=1)
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                height=600
            )
            
            # Export buttons
            col1, col2 = st.columns(2)
            
            with col1:
                # Original CSV export
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar CSV",
                    data=csv,
                    file_name=f"reporte_alarmas_{current_env}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # Important alarms CSV export (using cached data)
                important_csv = self._generate_important_alarms_csv_fast()
                st.download_button(
                    label="🚨 Descargar alarmas importantes",
                    data=important_csv,
                    file_name=f"alarmas_importantes_global_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info(f"No se encontraron instancias con alarmas en el entorno {current_env}")
    
    def _process_alarm_data(self, instances_data: List[Dict], environment: str) -> List[Dict]:
        """Process instance and alarm data to create report rows."""        
        report_rows = []
        
        for instance in instances_data:
            # Get all alarms for this instance
            instance_id = instance['ID']
            alarms = self.aws_service.get_alarms_for_instance(instance_id)
            
            # Get the real disk count from the instance data
            disk_count = instance.get('DiskCount', 0)  # Default to 0 if not found
            
            # Initialize counters
            alarm_counts = {
                'cpu_alarms': 0,
                'ram_alarms': 0,
                'disk_alarms': 0,
                'ping_alarms': 0,
                'other_alarms': 0,
                'insufficient_data': 0,
                'yellow_alarms': 0,
                'red_alarms': 0,
                'total_alarms': len(alarms)
            }
            
            # Process each alarm
            for alarm in alarms:
                alarm_name = alarm.get('AlarmName', '').upper()
                state = alarm.get('StateValue', '')
                
                # Categorize alarm type
                if any(kw in alarm_name for kw in ['CPU', 'PROCESSOR']):
                    alarm_counts['cpu_alarms'] += 1
                elif any(kw in alarm_name for kw in ['RAM', 'MEMORY', 'MEMORIA']):
                    alarm_counts['ram_alarms'] += 1
                elif self._is_disk_alarm(alarm_name):
                    alarm_counts['disk_alarms'] += 1
                elif any(kw in alarm_name for kw in ['PING', 'ICMP']):
                    alarm_counts['ping_alarms'] += 1
                else:
                    alarm_counts['other_alarms'] += 1
                
                # Count by state
                if state == 'INSUFFICIENT_DATA':
                    alarm_counts['insufficient_data'] += 1
                elif state == 'ALARM':
                    # Check if it's a preventive (yellow) alarm
                    if any(kw in alarm_name for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA']):
                        alarm_counts['yellow_alarms'] += 1
                    else:
                        alarm_counts['red_alarms'] += 1
            
            # Create row data
            row = {
                'instance_name': instance.get('Name', instance_id),
                'private_ip': instance.get('PrivateIP', 'N/A'),
                'instance_id': instance_id,
                'disk_count': disk_count,
                **alarm_counts
            }
            
            report_rows.append(row)
        
        return report_rows
    
    def _is_disk_alarm(self, alarm_name: str) -> bool:
        """Check if an alarm is disk-related."""
        disk_keywords = ['DISK', 'DISCO', 'STORAGE', 'FILESYSTEM', 'VOLUME']
        return any(kw in alarm_name.upper() for kw in disk_keywords)
    
    def _apply_row_highlight_styles(self, row):
        """Applies row highlighting based on alarm status."""
        
        style = ''
        if row['Alarmas Rojas'] > 0:
            style = 'background-color: #ffcccc; color: black;'
        elif row['Alarmas Amarillas'] > 0:
            style = 'background-color: #fff4cc; color: black;'
        elif row['Datos Insuficientes'] > 0:
            style = 'background-color: #e6e6e6; color: black;'
        
        return [style] * len(row)

    def _apply_validation_styles(self, row):
        """Applies cell-specific validation highlighting."""
        styles = [''] * len(row)
        
        # Helper to find index safely
        def get_col_index(col_name):
            try:
                return list(row.index).index(col_name)
            except ValueError:
                return -1

        border_style = ' box-shadow: inset 0 0 0 2px red;'

        # CPU validation
        cpu_idx = get_col_index('Alarmas CPU')
        if cpu_idx != -1 and row['Alarmas CPU'] != 2:
            styles[cpu_idx] += border_style

        # RAM validation
        ram_idx = get_col_index('Alarmas RAM')
        if ram_idx != -1 and row['Alarmas RAM'] == 0:
            styles[ram_idx] += border_style

        # Disk validation
        disk_idx = get_col_index('Alarmas Disco')
        if disk_idx != -1 and row['Cant. Discos'] > 0 and row['Alarmas Disco'] != (row['Cant. Discos'] * 3):
            styles[disk_idx] += border_style

        # Ping validation
        ping_idx = get_col_index('Alarmas Ping')
        if ping_idx != -1 and row['Alarmas Ping'] == 0:
            styles[ping_idx] += border_style
            
        return styles

    def _generate_important_alarms_csv(self, instances_data: List[Dict], environment: str) -> str:
        """Generate CSV for important alarms (red and insufficient data) across all environments."""
        import io
        from datetime import datetime
        
        # Get ALL instances data (not just filtered by current environment)
        all_instances_data = self.aws_service.get_aws_data()
        
        output = io.StringIO()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Process red alarms by environment
        environments = ["Production", "QA", "DEV"]
        
        for env in environments:
            # Filter instances by environment
            env_instances = [inst for inst in all_instances_data if inst.get('Environment') == env]
            
            if not env_instances:
                continue
            
            # --- New: Pre-process to get total count ---
            total_red_alarms_in_env = 0
            env_red_alarm_details = []
            for instance in env_instances:
                instance_id = instance['ID']
                alarms = self.aws_service.get_alarms_for_instance(instance_id)
                
                red_alarm_names = []
                for alarm in alarms:
                    alarm_name = alarm.get('AlarmName', '')
                    state = alarm.get('StateValue', '')
                    if state == 'ALARM' and not any(kw in alarm_name.upper() for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA']):
                        red_alarm_names.append(alarm_name)
                
                if red_alarm_names:
                    total_red_alarms_in_env += len(red_alarm_names)
                    env_red_alarm_details.append({
                        'name': instance.get('Name', instance_id),
                        'count': len(red_alarm_names),
                        'alarms': '; '.join(red_alarm_names)
                    })
            # --- End of Pre-processing ---

            # Header for this environment with total count
            output.write(f"Alertas Importantes Rojas,{env},{current_time},Total Alarmas Rojas: {total_red_alarms_in_env}\n")
            output.write("Nombre del Servidor,Cantidad,Nombre de alertas rojas\n")
            
            # Process red alarms for this environment
            if env_red_alarm_details:
                for detail in env_red_alarm_details:
                    output.write(f"{detail['name']},{detail['count']},\"{detail['alarms']}\"\n")
            else:
                output.write(f"No hay alertas rojas en {env}\n")
            
            # Add blank line after each environment section
            output.write("\n")
        
        # Section for insufficient data alarms (all environments together)
        output.write("Alertas No disponibles\n")
        output.write("Nombre del Servidor,Entorno,Cantidad,Nombre de la alerta que tiene datos no suficientes\n")
        
        # Process insufficient data alarms from all environments
        insufficient_alarms_found = False
        for instance in all_instances_data:
            instance_name = instance.get('Name', instance.get('ID', 'N/A'))
            instance_id = instance['ID']
            instance_env = instance.get('Environment', 'N/A')
            
            # Get alarms using the same method as the report
            alarms = self.aws_service.get_alarms_for_instance(instance_id)
            
            # Get all alarm names that are in INSUFFICIENT_DATA state (gray)
            insufficient_alarm_names = []
            for alarm in alarms:
                alarm_name = alarm.get('AlarmName', '')
                state = alarm.get('StateValue', '')
                
                if state in ['INSUFFICIENT_DATA', 'UNKNOWN']:
                    insufficient_alarm_names.append(alarm_name)
            
            if insufficient_alarm_names:
                insufficient_alarms_found = True
                alarm_count = len(insufficient_alarm_names)
                alarm_list = '; '.join(insufficient_alarm_names)
                output.write(f"{instance_name},{instance_env},{alarm_count},\"{alarm_list}\"\n")
        
        if not insufficient_alarms_found:
            output.write("No hay alertas con datos insuficientes\n")
        
        csv_content = output.getvalue()
        output.close()
        return csv_content

    def _generate_important_alarms_csv_fast(self) -> str:
        """Generate CSV for important alarms using cached AWS data (much faster)."""
        import io
        from datetime import datetime
        
        # Use cached data - no additional AWS calls!
        all_instances_data = self.aws_service.get_aws_data()
        
        output = io.StringIO()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Process red alarms by environment
        environments = ["Production", "QA", "DEV"]
        
        for env in environments:
            # Filter instances by environment
            env_instances = [inst for inst in all_instances_data if inst.get('Environment') == env]
            
            if not env_instances:
                continue
            
            # Pre-process to get total count using CACHED alarm data
            total_red_alarms_in_env = 0
            env_red_alarm_details = []
            
            for instance in env_instances:
                instance_id = instance['ID']
                # Use CACHED alarms from the instance data itself
                cached_alarms = instance.get('AlarmDetails', [])
                
                red_alarm_names = []
                for alarm in cached_alarms:
                    alarm_name = alarm.get('AlarmName', '')
                    state = alarm.get('StateValue', '')
                    if state == 'ALARM' and not any(kw in alarm_name.upper() for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA']):
                        red_alarm_names.append(alarm_name)
                
                if red_alarm_names:
                    total_red_alarms_in_env += len(red_alarm_names)
                    env_red_alarm_details.append({
                        'name': instance.get('Name', instance_id),
                        'count': len(red_alarm_names),
                        'alarms': '; '.join(red_alarm_names)
                    })

            # Header for this environment with total count
            output.write(f"Alertas Importantes Rojas,{env},{current_time},Total Alarmas Rojas: {total_red_alarms_in_env}\n")
            output.write("Nombre del Servidor,Cantidad,Nombre de alertas rojas\n")
            
            # Process red alarms for this environment
            if env_red_alarm_details:
                for detail in env_red_alarm_details:
                    output.write(f"{detail['name']},{detail['count']},\"{detail['alarms']}\"\n")
            else:
                output.write(f"No hay alertas rojas en {env}\n")
            
            # Add blank line after each environment section
            output.write("\n")
        
        # Section for insufficient data alarms (all environments together)
        output.write("Alertas No disponibles\n")
        output.write("Nombre del Servidor,Entorno,Cantidad,Nombre de la alerta que tiene datos no suficientes\n")
        
        # Process insufficient data alarms from all environments using cached data
        insufficient_alarms_found = False
        for instance in all_instances_data:
            instance_name = instance.get('Name', instance.get('ID', 'N/A'))
            instance_env = instance.get('Environment', 'N/A')
            # Use CACHED alarms
            cached_alarms = instance.get('AlarmDetails', [])
            
            # Get all alarm names that are in INSUFFICIENT_DATA state (gray)
            insufficient_alarm_names = []
            for alarm in cached_alarms:
                alarm_name = alarm.get('AlarmName', '')
                state = alarm.get('StateValue', '')
                
                if state in ['INSUFFICIENT_DATA', 'UNKNOWN']:
                    insufficient_alarm_names.append(alarm_name)
            
            if insufficient_alarm_names:
                insufficient_alarms_found = True
                alarm_count = len(insufficient_alarm_names)
                alarm_list = '; '.join(insufficient_alarm_names)
                output.write(f"{instance_name},{instance_env},{alarm_count},\"{alarm_list}\"\n")
        
        if not insufficient_alarms_found:
            output.write("No hay alertas con datos insuficientes\n")
        
        csv_content = output.getvalue()
        output.close()
        return csv_content