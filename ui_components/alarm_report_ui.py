"""
Alarm Report UI component for displaying global alarm statistics.
"""
import streamlit as st # type: ignore
import pandas as pd # pyright: ignore[reportMissingModuleSource]
from typing import Dict, List
from collections import Counter, defaultdict
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
            # Preserve columns parameter when returning to dashboard
            columns_param = st.query_params.get('columns', '2')
            if st.button("← Volver al Dashboard", type="secondary"):
                # Clear alarm_report query param and preserve columns
                st.query_params.clear()
                st.query_params.update({"columns": columns_param})
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
            df['total_alarms_theoretical'] = 2 + 1 + (df['disk_count'] * 2) + 1
            
            # Define column order and names
            column_order = [
                'instance_name', 'private_ip', 'instance_id',
                'cpu_alarms', 'ram_alarms', 'disk_alarms', 'disk_count',
                'ping_alarms', 'availability_alarms', 'sap_process_alarms', 'other_alarms',
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
                'availability_alarms': 'A. Disponibilidad',
                'sap_process_alarms': 'A. Procesos SAP',
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
            df = df.sort_values(by='Nombre Instancia').reset_index(drop=True) # type: ignore

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

            st.info("Se consideran alarmas amarillas las alarmas proactivas y de alerta. Las alarmas de disco deben ser 2x la cantidad de discos.")
            
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
                # Problem report document
                problem_report_txt = self._generate_problem_report_txt(report_data, filtered_instances)
                st.download_button(
                    label="📄 Documento de Alarmas con Problemas",
                    data=problem_report_txt,
                    file_name=f"reporte_problemas_alarmas_{current_env}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                # New report by type
                problem_report_by_type_txt = self._generate_problem_report_by_type_txt(report_data, filtered_instances)
                st.download_button(
                    label="📊 Alarmas con problemas por tipo",
                    data=problem_report_by_type_txt,
                    file_name=f"reporte_problemas_por_tipo_{current_env}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
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
            # Use the pre-fetched alarms from the main data structure for efficiency
            alarms = instance.get('AlarmObjects', [])
            
            # Get the real disk count from the instance data
            disk_count = instance.get('DiskCount', 0)  # Default to 0 if not found
            
            # Initialize details dictionary
            alarm_details = {
                'cpu_alarms': 0,
                'ram_alarms': 0,
                'disk_alarms': 0,
                'ping_alarms': 0,
                'availability_alarms': 0,
                'sap_process_alarms': 0,
                'other_alarms': 0,
                'insufficient_data': 0,
                'yellow_alarms': 0,
                'red_alarms': 0,
                'total_alarms': len(alarms),
                'other_alarm_names': [],
                'red_alarm_names': [],
                'insufficient_data_alarm_names': []
            }
            
            # Process each alarm
            for alarm in alarms:
                # Use original case for names, but upper for matching
                original_alarm_name = alarm.get('AlarmName', '')
                alarm_name_upper = original_alarm_name.upper()
                state = alarm.get('StateValue', '')
                
                # Categorize alarm type
                if any(kw in alarm_name_upper for kw in ['CPU', 'PROCESSOR']):
                    alarm_details['cpu_alarms'] += 1
                elif any(kw in alarm_name_upper for kw in ['RAM', 'MEMORY', 'MEMORIA']):
                    alarm_details['ram_alarms'] += 1
                elif self._is_disk_alarm(alarm_name_upper):
                    alarm_details['disk_alarms'] += 1
                elif any(kw in alarm_name_upper for kw in ['PING', 'ICMP']):
                    alarm_details['ping_alarms'] += 1
                elif alarm_name_upper.endswith('AVAILABILITY'):
                    alarm_details['availability_alarms'] += 1
                elif alarm_name_upper.endswith('SAP PROCESS RUNNING'):
                    alarm_details['sap_process_alarms'] += 1
                else:
                    alarm_details['other_alarms'] += 1
                    alarm_details['other_alarm_names'].append(original_alarm_name)
                
                # Count by state
                if state == 'INSUFFICIENT_DATA':
                    alarm_details['insufficient_data'] += 1
                    alarm_details['insufficient_data_alarm_names'].append(original_alarm_name)
                elif state == 'ALARM':
                    # Check if it's a preventive (yellow) alarm
                    if any(kw in alarm_name_upper for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA', 'SMDA98']):
                        alarm_details['yellow_alarms'] += 1
                    else:
                        alarm_details['red_alarms'] += 1
                        alarm_details['red_alarm_names'].append(original_alarm_name)
            
            # Create row data
            row = {
                'instance_name': instance.get('Name', instance_id),
                'private_ip': instance.get('PrivateIP', 'N/A'),
                'instance_id': instance_id,
                'disk_count': disk_count,
                **alarm_details
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
        if disk_idx != -1 and row['Cant. Discos'] > 0 and row['Alarmas Disco'] != (row['Cant. Discos'] * 2):
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
                    if state == 'ALARM' and not any(kw in alarm_name.upper() for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA', 'SMDA98']):
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
                    if state == 'ALARM' and not any(kw in alarm_name.upper() for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA', 'SMDA98']):
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
    def _generate_important_alarms_csv(self, all_instances_data: list) -> str:
        """Generate CSV for important alarms using the pre-fetched instance data."""
        import io
        from datetime import datetime
        
        output = io.StringIO()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # --- Red Alarms Section ---
        for env in ["Production", "QA", "DEV"]:
            env_instances = [inst for inst in all_instances_data if inst.get('Environment') == env]
            if not env_instances:
                output.write(f"Alertas Importantes Rojas,{env},{current_time},Total Alarmas Rojas: 0\n")
                output.write("Nombre del Servidor,Cantidad,Nombre de alertas rojas\n")
                output.write(f"No hay alertas rojas en {env}\n\n")
                continue

            red_alarm_details = []
            total_red_alarms_in_env = 0

            for instance in env_instances:
                # Get alarms from the pre-fetched data
                alarms = instance.get('AlarmObjects', [])
                red_alarm_names = []
                for alarm in alarms:
                    alarm_name = alarm.get('AlarmName', '')
                    state = alarm.get('StateValue', '')
                    # Check for RED alarm state
                    if state == 'ALARM' and not any(kw in alarm_name.upper() for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA', 'SMDA98']):
                        red_alarm_names.append(alarm_name)
                
                if red_alarm_names:
                    total_red_alarms_in_env += len(red_alarm_names)
                    red_alarm_details.append({
                        'name': instance.get('Name', instance.get('ID')),
                        'count': len(red_alarm_names),
                        'alarms': '; '.join(red_alarm_names)
                    })

            # Write header and data for the environment
            output.write(f"Alertas Importantes Rojas,{env},{current_time},Total Alarmas Rojas: {total_red_alarms_in_env}\n")
            output.write("Nombre del Servidor,Cantidad,Nombre de alertas rojas\n")
            
            if red_alarm_details:
                for detail in red_alarm_details:
                    output.write(f"{detail['name']},{detail['count']},\"{detail['alarms']}\"\n")
            else:
                output.write(f"No hay alertas rojas en {env}\n")
            output.write("\n")

        # --- Insufficient Data Alarms Section ---
        output.write("Alertas No disponibles\n")
        output.write("Nombre del Servidor,Entorno,Cantidad,Nombre de la alerta que tiene datos no suficientes\n")
        
        insufficient_alarms_found = False
        # Filter for only instances that have insufficient data alarms to avoid iterating all instances again
        instances_with_insufficient = [
            inst for inst in all_instances_data 
            if any(alarm.get('StateValue') in ['INSUFFICIENT_DATA', 'UNKNOWN'] for alarm in inst.get('AlarmObjects', []))
        ]

        if instances_with_insufficient:
            insufficient_alarms_found = True
            for instance in instances_with_insufficient:
                alarms = instance.get('AlarmObjects', [])
                insufficient_alarm_names = [
                    alarm.get('AlarmName', '') 
                    for alarm in alarms 
                    if alarm.get('StateValue') in ['INSUFFICIENT_DATA', 'UNKNOWN']
                ]
                
                if insufficient_alarm_names:
                    instance_name = instance.get('Name', instance.get('ID'))
                    instance_env = instance.get('Environment', 'N/A')
                    alarm_count = len(insufficient_alarm_names)
                    alarm_list = '; '.join(insufficient_alarm_names)
                    output.write(f"{instance_name},{instance_env},{alarm_count},\"{alarm_list}\"\n")

        if not insufficient_alarms_found:
            output.write("No hay alertas con datos insuficientes\n")
            
        csv_content = output.getvalue()
        output.close()
        return csv_content

    def _generate_problem_report_txt(self, report_data: List[Dict], instances_data: List[Dict]) -> str:
        """Generate a text document outlining missing and problematic alarms for each instance."""
        import io
        from datetime import datetime

        output = io.StringIO()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        output.write(f"Reporte de Alarmas con Problemas - Generado: {current_time}\n")
        output.write("="*80 + "\n\n")

        # Create a lookup for instance state
        instance_states = {inst['ID']: inst.get('State', 'unknown') for inst in instances_data}
        
        running_instances = []
        stopped_instances = []

        for instance_data in report_data:
            instance_id = instance_data.get('instance_id', '')
            if instance_states.get(instance_id) == 'stopped':
                stopped_instances.append(instance_data)
            else:
                running_instances.append(instance_data)

        # --- Process Running Instances ---
        output.write("--- INSTANCIAS ENCENDIDAS ---\n\n")
        for instance_data in running_instances:
            problems = self._get_instance_problems(instance_data, is_stopped=False)
            if problems:
                instance_name = instance_data.get('instance_name', 'N/A')
                output.write(f"Instancia: {instance_name}\n")
                output.write("-" * len(f"Instancia: {instance_name}\n"))
                output.write("\n")
                output.write("".join(problems))
                output.write("\n")

        # --- Process Stopped Instances ---
        if stopped_instances:
            output.write("\n" + "="*80 + "\n")
            output.write("--- INSTANCIAS APAGADAS ---\n\n")
            for instance_data in stopped_instances:
                problems = self._get_instance_problems(instance_data, is_stopped=True)
                if problems:
                    instance_name = instance_data.get('instance_name', 'N/A')
                    output.write(f"Instancia: {instance_name}\n")
                    output.write("-" * len(f"Instancia: {instance_name}\n"))
                    output.write("\n")
                    output.write("".join(problems))
                    output.write("\n")

        report_content = output.getvalue()
        output.close()
        return report_content

    def _get_instance_problems(self, instance_data: Dict, is_stopped: bool) -> List[str]:
        """Helper function to get a list of problem strings for an instance."""
        problems = []
        
        # Check for missing alarms
        if instance_data.get('cpu_alarms', 0) != 2:
            problems.append(f"- Faltan {2 - instance_data.get('cpu_alarms', 0)} alarma(s) de CPU.\n")
        if instance_data.get('ram_alarms', 0) == 0:
            problems.append("- Falta alarma de RAM.\n")
        
        disk_count = instance_data.get('disk_count', 0)
        if disk_count > 0 and instance_data.get('disk_alarms', 0) != (disk_count * 2):
            expected = disk_count * 2
            actual = instance_data.get('disk_alarms', 0)
            problems.append(f"- Faltan {expected - actual} alarma(s) de Disco (esperadas: {expected}, actuales: {actual}).\n")

        if instance_data.get('ping_alarms', 0) == 0:
            problems.append("- Falta alarma de Ping.\n")
        if instance_data.get('availability_alarms', 0) == 0:
            problems.append("- Falta alarma de Disponibilidad.\n")

        # List "Other" alarms
        other_alarms = instance_data.get('other_alarm_names', [])
        if other_alarms:
            problem_str = "- Alarmas en categoría 'Otras':\n"
            for name in other_alarms:
                problem_str += f"    - {name}\n"
            problems.append(problem_str)

        # List "Red" alarms only if instance is not stopped
        if not is_stopped:
            red_alarms = instance_data.get('red_alarm_names', [])
            if red_alarms:
                problem_str = "- Alarmas en estado ROJO (ALARM):\n"
                for name in red_alarms:
                    problem_str += f"    - {name}\n"
                problems.append(problem_str)

        # List "Insufficient Data" alarms only if instance is not stopped
        if not is_stopped:
            insufficient_alarms = instance_data.get('insufficient_data_alarm_names', [])
            if insufficient_alarms:
                problem_str = "- Alarmas con DATOS INSUFICIENTES:\n"
                for name in insufficient_alarms:
                    problem_str += f"    - {name}\n"
                problems.append(problem_str)
        
        return problems
    
    def _generate_problem_report_by_type_txt(self, report_data: List[Dict], instances_data: List[Dict]) -> str:
        """Generate a text document of problematic alarms, grouped by problem type."""
        import io
        from datetime import datetime
        from collections import defaultdict

        output = io.StringIO()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        output.write(f"Reporte de Alarmas con Problemas por Tipo - Generado: {current_time}\n")
        output.write("="*80 + "\n\n")

        # Create lookups for instance state and cpu options
        instance_details_map = {
            inst['ID']: {
                'State': inst.get('State', 'unknown'),
                'CpuOptions': inst.get('CpuOptions', {})
            } for inst in instances_data
        }
        
        problems_by_type = defaultdict(list)

        # --- Gather all problems ---
        for instance_data in report_data:
            instance_name = instance_data.get('instance_name', 'N/A')
            instance_id = instance_data.get('instance_id', '')
            
            details = instance_details_map.get(instance_id, {})
            instance_state = details.get('State', 'unknown')
            cpu_options = details.get('CpuOptions', {})

            suffix = " (actualmente servidor apagado)" if instance_state == 'stopped' else ""

            # Check for missing CPU alarms
            # Rule: 1 alarm per vCPU. vCPU = CoreCount * ThreadsPerCore
            vcpu_count = cpu_options.get('CoreCount', 1) * cpu_options.get('ThreadsPerCore', 1)
            current_cpu_alarms = instance_data.get('cpu_alarms', 0)
            if current_cpu_alarms < vcpu_count:
                missing_count = vcpu_count - current_cpu_alarms
                problems_by_type['Alarmas de CPU Faltantes'].append(
                    f"- {instance_name}: {current_cpu_alarms} Alarma(s), {vcpu_count} CPU, falta(n) {missing_count} alarma(s){suffix}\n"
                )

            # Check for missing RAM alarms
            if instance_data.get('ram_alarms', 0) == 0:
                problems_by_type['Alarmas de RAM Faltantes'].append(f"- {instance_name}{suffix}\n")
            
            # Check for missing Disk alarms
            disk_count = instance_data.get('disk_count', 0)
            if disk_count > 0 and instance_data.get('disk_alarms', 0) != (disk_count * 2):
                expected = disk_count * 2
                actual = instance_data.get('disk_alarms', 0)
                problems_by_type['Alarmas de Disco Faltantes'].append(f"- {instance_name}: Faltan {expected - actual} (esperadas: {expected}, actuales: {actual}){suffix}\n")

            # Check for missing Ping alarms
            if instance_data.get('ping_alarms', 0) == 0:
                problems_by_type['Alarmas de Ping Faltantes'].append(f"- {instance_name}{suffix}\n")
            
            # Check for missing Availability alarms
            if instance_data.get('availability_alarms', 0) == 0:
                problems_by_type['Alarmas de Disponibilidad Faltantes'].append(f"- {instance_name}{suffix}\n")

            # List "Other" alarms
            other_alarms = instance_data.get('other_alarm_names', [])
            if other_alarms:
                for name in other_alarms:
                    problems_by_type["Alarmas en categoría 'Otras'"].append(f"- {instance_name}: {name}{suffix}\n")

            # List "Red" alarms (only for running instances)
            red_alarms = instance_data.get('red_alarm_names', [])
            if red_alarms and instance_state != 'stopped':
                for name in red_alarms:
                    problems_by_type["Alarmas en estado ROJO (ALARM)"].append(f"- {instance_name}: {name}\n")

            # List "Insufficient Data" alarms (only for running instances)
            insufficient_alarms = instance_data.get('insufficient_data_alarm_names', [])
            if insufficient_alarms and instance_state != 'stopped':
                for name in insufficient_alarms:
                    problems_by_type["Alarmas con DATOS INSUFICIENTES"].append(f"- {instance_name}: {name}\n")

        # --- Write the report from the grouped problems ---
        if not problems_by_type:
            output.write("No se encontraron problemas en las alarmas de las instancias analizadas.\n")
        else:
            # Define a specific order for the report sections
            section_order = [
                'Alarmas de CPU Faltantes',
                'Alarmas de RAM Faltantes',
                'Alarmas de Disco Faltantes',
                'Alarmas de Ping Faltantes',
                'Alarmas de Disponibilidad Faltantes',
                "Alarmas en estado ROJO (ALARM)",
                "Alarmas con DATOS INSUFICIENTES",
                "Alarmas en categoría 'Otras'"
            ]
            for title in section_order:
                if title in problems_by_type:
                    problems = problems_by_type[title]
                    output.write(f"{title}:\n")
                    output.write("-" * (len(title) + 1) + "\n")
                    for problem in problems:
                        output.write(problem)
                    output.write("\n")

        report_content = output.getvalue()
        output.close()
        return report_content