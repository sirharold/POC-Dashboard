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
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(
                f"<a href='/' style='text-decoration: none; color: #0066cc; font-size: 0.9rem; margin-top: 1rem; display: inline-block;'>← Volver al Dashboard</a>",
                unsafe_allow_html=True
            )
        
        # Page title
        st.markdown("# 📊 Reporte Global de Alarmas")
        
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

            # --- Data Transformation for Display --- #
            # Create a copy for display purposes and another for tooltips
            display_df = df.copy().astype(str)
            tooltips_df = pd.DataFrame('', index=df.index, columns=df.columns)

            # Apply validation rules and generate tooltips/icons
            for i, row in df.iterrows():
                # CPU
                if row['Alarmas CPU'] != 2:
                    display_df.at[i, 'Alarmas CPU'] = f"{row['Alarmas CPU']} ⚠️"
                    tooltips_df.at[i, 'Alarmas CPU'] = f"Se esperaban 2 alarmas de CPU, pero se encontraron {row['Alarmas CPU']}."
                # RAM
                if row['Alarmas RAM'] == 0:
                    display_df.at[i, 'Alarmas RAM'] = f"{row['Alarmas RAM']} ⚠️"
                    tooltips_df.at[i, 'Alarmas RAM'] = "Se esperaba 1 alarma de RAM, pero se encontraron 0."
                # Disk
                expected_disk_alarms = row['Cant. Discos'] * 3
                if row['Cant. Discos'] > 0 and row['Alarmas Disco'] != expected_disk_alarms:
                    display_df.at[i, 'Alarmas Disco'] = f"{row['Alarmas Disco']} ⚠️"
                    tooltips_df.at[i, 'Alarmas Disco'] = f"Se esperaban {expected_disk_alarms} alarmas de disco ({row['Cant. Discos']} * 3), pero se encontraron {row['Alarmas Disco']}."
                # Ping
                if row['Alarmas Ping'] == 0:
                    display_df.at[i, 'Alarmas Ping'] = f"{row['Alarmas Ping']} ⚠️"
                    tooltips_df.at[i, 'Alarmas Ping'] = "Se esperaba 1 alarma de Ping, pero se encontraron 0."

            # --- End of Data Transformation ---

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

            st.info("Se consideran alarmas amarillas las alarmas proactivas y de alerta. Las alarmas de disco deben ser 3x la cantidad de discos. La cantidad de alertas de CPU debieran ser dos")
            
            st.markdown("---")
            
            # Display the table
            st.markdown("### 📋 Detalle por Instancia")
            
            # Apply custom styling to the dataframe
            styled_df = display_df.style.apply(self._apply_row_highlight_styles, axis=1).set_tooltips(tooltips_df)
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                height=600
            )
            
            # Export button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"reporte_alarmas_{current_env}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
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