
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
        columns_param = st.query_params.get('columns', '2')
        if st.button("← Volver al Dashboard", type="secondary"):
            st.query_params.clear()
            st.query_params.update({"columns": columns_param})
            st.rerun()
        
        st.markdown(f"<h3 style='text-align: center; margin: 0;'>Reporte Global de Alarmas</h3>", unsafe_allow_html=True)
        
        # Get all instance data with alarms that have the DashboardGroup tag
        instances_data = self.aws_service.get_aws_data()
        
        # Process alarm data for all instances
        report_data = self._process_alarm_data(instances_data)
        
        if not report_data:
            st.info("No se encontraron instancias con la etiqueta 'DashboardGroup' en ningún entorno.")
            return

        # --- Create and Display Report Table ---
        df = pd.DataFrame(report_data)

        # Add Theoretical Alarms Column (1 CPU + 1 RAM + 2*disks + 1 ping)
        df['total_alarms_theoretical'] = 1 + 1 + (df['disk_count'] * 2) + 1
        
        # Define column order and names
        column_order = [
            'instance_name', 'environment', 'private_ip', 'instance_id',
            'cpu_alarms', 'ram_alarms', 'disk_alarms', 'disk_count',
            'ping_alarms', 'availability_alarms', 'sap_process_alarms', 'other_alarms',
            'insufficient_data', 'yellow_alarms', 'red_alarms',
            'total_alarms_theoretical', 'total_alarms'
        ]
        
        column_names = {
            'instance_name': 'Nombre Instancia', 'environment': 'Entorno', 'private_ip': 'IP Privada',
            'instance_id': 'Instance ID', 'cpu_alarms': 'Alarmas CPU', 'ram_alarms': 'Alarmas RAM',
            'disk_alarms': 'Alarmas Disco', 'disk_count': 'Cant. Discos', 'ping_alarms': 'Alarmas Ping',
            'availability_alarms': 'A. Disponibilidad', 'sap_process_alarms': 'A. Procesos SAP',
            'other_alarms': 'Otras Alarmas', 'insufficient_data': 'Datos Insuficientes',
            'yellow_alarms': 'Alarmas Amarillas', 'red_alarms': 'Alarmas Rojas',
            'total_alarms_theoretical': 'T. A. Teóricas', 'total_alarms': 'T. A. Actuales'
        }
        
        df = df[column_order]
        df.columns = [column_names[col] for col in column_order]

        # Sort by environment and then instance name
        df = df.sort_values(by=['Entorno', 'Nombre Instancia']).reset_index(drop=True)

        # --- Display Summary Stats ---
        st.markdown("### 📈 Resumen Global")
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
        st.divider()
        
        # --- Display Main Table ---
        st.markdown("### 📋 Detalle por Instancia (Todos los Entornos)")
        styled_df = df.style.apply(self._apply_row_highlight_styles, axis=1).apply(self._apply_validation_styles, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=600)
        
        # --- Export Buttons ---
        col1, col2 = st.columns(2)
        with col1:
            problem_report_txt = self._generate_problem_report_txt(report_data, instances_data)
            st.download_button(
                label="📄 Documento de Alarmas con Problemas",
                data=problem_report_txt,
                file_name=f"reporte_problemas_alarmas_global_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain", use_container_width=True
            )
        
        with col2:
            problem_report_by_type_txt = self._generate_problem_report_by_type_txt(report_data, instances_data)
            st.download_button(
                label="📊 Alarmas con problemas por tipo",
                data=problem_report_by_type_txt,
                file_name=f"reporte_problemas_por_tipo_global_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain", use_container_width=True
            )
    
    def _process_alarm_data(self, instances_data: List[Dict]) -> List[Dict]:
        """Process instance and alarm data to create report rows."""        
        report_rows = []
        for instance in instances_data:
            alarms = instance.get('AlarmObjects', [])
            alarm_details = {
                'cpu_alarms': 0, 'ram_alarms': 0, 'disk_alarms': 0, 'ping_alarms': 0,
                'availability_alarms': 0, 'sap_process_alarms': 0, 'other_alarms': 0,
                'insufficient_data': 0, 'yellow_alarms': 0, 'red_alarms': 0,
                'total_alarms': len(alarms),
                'other_alarm_names': [], 'red_alarm_names': [], 'insufficient_data_alarm_names': []
            }
            
            for alarm in alarms:
                name_upper = alarm.get('AlarmName', '').upper()
                state = alarm.get('StateValue', '')
                
                if any(kw in name_upper for kw in ['CPU', 'PROCESSOR']): alarm_details['cpu_alarms'] += 1
                elif any(kw in name_upper for kw in ['RAM', 'MEMORY', 'MEMORIA']): alarm_details['ram_alarms'] += 1
                elif self._is_disk_alarm(name_upper): alarm_details['disk_alarms'] += 1
                elif any(kw in name_upper for kw in ['PING', 'ICMP']): alarm_details['ping_alarms'] += 1
                elif name_upper.endswith('AVAILABILITY'): alarm_details['availability_alarms'] += 1
                elif name_upper.endswith('SAP PROCESS RUNNING'): alarm_details['sap_process_alarms'] += 1
                else:
                    alarm_details['other_alarms'] += 1
                    alarm_details['other_alarm_names'].append(alarm.get('AlarmName', ''))
                
                if state == 'INSUFFICIENT_DATA':
                    alarm_details['insufficient_data'] += 1
                    alarm_details['insufficient_data_alarm_names'].append(alarm.get('AlarmName', ''))
                elif state == 'ALARM':
                    if any(kw in name_upper for kw in ['ALERTA', 'PROACTIVA', 'PREVENTIVA', 'SMDA98']):
                        alarm_details['yellow_alarms'] += 1
                    else:
                        alarm_details['red_alarms'] += 1
                        alarm_details['red_alarm_names'].append(alarm.get('AlarmName', ''))
            
            report_rows.append({
                'instance_name': instance.get('Name', instance['ID']),
                'environment': instance.get('Environment', 'Unknown'),
                'private_ip': instance.get('PrivateIP', 'N/A'),
                'instance_id': instance['ID'],
                'disk_count': instance.get('DiskCount', 0),
                **alarm_details
            })
        return report_rows
    
    def _is_disk_alarm(self, alarm_name: str) -> bool:
        """Check if an alarm is disk-related."""
        return any(kw in alarm_name.upper() for kw in ['DISK', 'DISCO', 'STORAGE', 'FILESYSTEM', 'VOLUME'])
    
    def _apply_row_highlight_styles(self, row):
        """Applies row highlighting based on alarm status."""
        style = ''
        if row['Alarmas Rojas'] > 0: style = 'background-color: #ffcccc; color: black;'
        elif row['Alarmas Amarillas'] > 0: style = 'background-color: #fff4cc; color: black;'
        elif row['Datos Insuficientes'] > 0: style = 'background-color: #e6e6e6; color: black;'
        return [style] * len(row)

    def _apply_validation_styles(self, row):
        """Applies cell-specific validation highlighting."""
        styles = [''] * len(row)
        def get_col_index(col_name):
            try: return list(row.index).index(col_name)
            except ValueError: return -1
        border = ' box-shadow: inset 0 0 0 2px red;'
        if (idx := get_col_index('Alarmas CPU')) != -1 and row['Alarmas CPU'] != 1: styles[idx] += border
        if (idx := get_col_index('Alarmas RAM')) != -1 and row['Alarmas RAM'] == 0: styles[idx] += border
        if (idx := get_col_index('Alarmas Disco')) != -1 and row['Cant. Discos'] > 0 and row['Alarmas Disco'] != (row['Cant. Discos'] * 2): styles[idx] += border
        if (idx := get_col_index('Alarmas Ping')) != -1 and row['Alarmas Ping'] == 0: styles[idx] += border
        return styles

    def _generate_problem_report_txt(self, report_data: List[Dict], instances_data: List[Dict]) -> str:
        """Generate a text document outlining missing and problematic alarms for each instance."""
        import io; from datetime import datetime
        output = io.StringIO()
        output.write(f"Reporte de Alarmas con Problemas (Global) - Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*80}\n\n")
        
        instance_states = {inst['ID']: inst.get('State', 'unknown') for inst in instances_data}
        running_instances = sorted([rd for rd in report_data if instance_states.get(rd['instance_id']) != 'stopped'], key=lambda x: (x.get('environment', 'z'), x.get('instance_name', 'z')))
        stopped_instances = sorted([rd for rd in report_data if instance_states.get(rd['instance_id']) == 'stopped'], key=lambda x: (x.get('environment', 'z'), x.get('instance_name', 'z')))

        def write_problems_for_section(title, instances):
            output.write(f"--- {title} ---\n\n")
            if not instances:
                output.write(f"No hay instancias en esta categoría con problemas.\n\n")
                return
            for inst_data in instances:
                problems = self._get_instance_problems(inst_data, is_stopped=(title == "INSTANCIAS APAGADAS"))
                if problems:
                    header = f"Instancia: {inst_data['instance_name']} (Entorno: {inst_data['environment']})"
                    output.write(f"{header}\n{'-' * len(header)}\n{''.join(problems)}\n")
        
        write_problems_for_section("INSTANCIAS ENCENDIDAS", running_instances)
        if stopped_instances:
            output.write(f"\n{'='*80}\n")
            write_problems_for_section("INSTANCIAS APAGADAS", stopped_instances)

        return output.getvalue()

    def _get_instance_problems(self, inst: Dict, is_stopped: bool) -> List[str]:
        """Helper function to get a list of problem strings for an instance."""
        problems = []
        if inst['cpu_alarms'] != 1: problems.append(f"- Tiene {inst['cpu_alarms']} alarma(s) de CPU (esperada: 1).\n")
        if inst['ram_alarms'] == 0: problems.append("- Falta alarma de RAM.\n")
        if inst['disk_count'] > 0 and inst['disk_alarms'] != (inst['disk_count'] * 2):
            problems.append(f"- Faltan {inst['disk_count']*2 - inst['disk_alarms']} alarma(s) de Disco (esperadas: {inst['disk_count']*2}, actuales: {inst['disk_alarms']}).\n")
        if inst['ping_alarms'] == 0: problems.append("- Falta alarma de Ping.\n")
        if inst['availability_alarms'] == 0: problems.append("- Falta alarma de Disponibilidad.\n")
        if others := inst['other_alarm_names']:
            problems.append("- Alarmas en categoría 'Otras':\n" + "".join([f"    - {name}\n" for name in others]))
        if not is_stopped:
            if reds := inst['red_alarm_names']:
                problems.append("- Alarmas en estado ROJO (ALARM):\n" + "".join([f"    - {name}\n" for name in reds]))
            if insuff := inst['insufficient_data_alarm_names']:
                problems.append("- Alarmas con DATOS INSUFICIENTES:\n" + "".join([f"    - {name}\n" for name in insuff]))
        return problems
    
    def _generate_problem_report_by_type_txt(self, report_data: List[Dict], instances_data: List[Dict]) -> str:
        """Generate a text document of problematic alarms, grouped by problem type."""
        import io; from datetime import datetime; from collections import defaultdict
        output = io.StringIO()
        output.write(f"Reporte de Alarmas con Problemas por Tipo (Global) - Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*80}\n\n")

        instance_states = {inst['ID']: inst.get('State', 'unknown') for inst in instances_data}
        problems_by_type = defaultdict(list)

        for inst in report_data:
            state = instance_states.get(inst['instance_id'], 'unknown')
            suffix = " (servidor apagado)" if state == 'stopped' else ""
            p_str = lambda details: f"- [{inst['environment']}] {inst['instance_name']}: {details}{suffix}\n"

            if inst['cpu_alarms'] != 1: problems_by_type['Alarmas de CPU Faltantes o Incorrectas'].append(p_str(f"Tiene {inst['cpu_alarms']} en lugar de 1."))
            if inst['ram_alarms'] == 0: problems_by_type['Alarmas de RAM Faltantes'].append(p_str("Falta alarma de RAM."))
            if inst['disk_count'] > 0 and inst['disk_alarms'] != inst['disk_count']*2:
                problems_by_type['Alarmas de Disco Faltantes'].append(p_str(f"Faltan {inst['disk_count']*2 - inst['disk_alarms']} (esperadas: {inst['disk_count']*2}, actuales: {inst['disk_alarms']})."))
            if inst['ping_alarms'] == 0: problems_by_type['Alarmas de Ping Faltantes'].append(p_str("Falta alarma de Ping."))
            if inst['availability_alarms'] == 0: problems_by_type['Alarmas de Disponibilidad Faltantes'].append(p_str("Falta alarma de Disponibilidad."))
            for name in inst['other_alarm_names']: problems_by_type["Alarmas en categoría 'Otras'"].append(p_str(name))
            if state != 'stopped':
                for name in inst['red_alarm_names']: problems_by_type["Alarmas en estado ROJO (ALARM)"].append(p_str(name))
                for name in inst['insufficient_data_alarm_names']: problems_by_type["Alarmas con DATOS INSUFICIENTES"].append(p_str(name))

        if not problems_by_type:
            output.write("No se encontraron problemas en las alarmas de las instancias analizadas.\n")
        else:
            section_order = ['Alarmas de CPU Faltantes o Incorrectas', 'Alarmas de RAM Faltantes', 'Alarmas de Disco Faltantes', 'Alarmas de Ping Faltantes', 'Alarmas de Disponibilidad Faltantes', "Alarmas en estado ROJO (ALARM)", "Alarmas con DATOS INSUFICIENTES", "Alarmas en categoría 'Otras'"]
            for title in section_order:
                if title in problems_by_type:
                    problems = sorted(problems_by_type[title])
                    header = f"{title} ({len(problems)})"
                    output.write(f"{header}:\n{'-' * (len(header) + 1)}\n{''.join(problems)}\n")
        return output.getvalue()
