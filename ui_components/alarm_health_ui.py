
"""
UI component for the Alarm Health Analysis page.
"""
import streamlit as st
from typing import Dict, List
import math

class AlarmHealthUI:
    """UI for displaying alarm health analysis."""

    def __init__(self, aws_service):
        """Initialize with AWS service dependency."""
        self.aws_service = aws_service

    def display_alarm_health_page(self):
        """Display the full alarm health analysis page."""
        # Add back to dashboard link
        columns_param = st.query_params.get('columns', '2')
        if st.button("← Volver al Dashboard", type="secondary"):
            st.query_params.clear()
            st.query_params.update({"columns": columns_param})
            st.rerun()

        st.info("Este reporte analiza todas las alarmas de CloudWatch para encontrar problemas comunes como alarmas huérfanas, duplicadas o con estados problemáticos persistentes.")

        if st.button("Recargar Análisis", help="Vuelve a ejecutar el análisis de salud de alarmas para obtener los datos más recientes."):
            if 'alarm_health_results' in st.session_state:
                del st.session_state['alarm_health_results']
            st.rerun()

        # Cache analysis results in session state
        if 'alarm_health_results' not in st.session_state:
            with st.spinner("Ejecutando análisis... Esto puede tardar uno o dos minutos."):
                st.session_state.alarm_health_results = self.aws_service.analyze_alarm_health()
        
        analysis_results = st.session_state.get('alarm_health_results')

        if not analysis_results or 'error' in analysis_results:
            error_msg = analysis_results.get('error', 'Unknown') if analysis_results else 'Unknown'
            st.error(f"No se pudo completar el análisis de alarmas. Error: {error_msg}")
            # Clear cached results on error to allow for a retry
            if 'alarm_health_results' in st.session_state:
                del st.session_state['alarm_health_results']
            return

        # --- Render Results with Checkboxes ---
        self._display_orphan_alarms(
            "🚨 Alarmas Huérfanas por Instancia Terminada",
            analysis_results.get('orphan_by_terminated_instance', [])
        )
        self._display_missing_dimension_alarms(
            "❓ Alarmas Sin Asociación Clara",
            analysis_results.get('orphan_by_missing_dimension', [])
        )
        self._display_duplicate_alarms(
            "👯‍♀️ Grupos de Alarmas Duplicadas",
            analysis_results.get('duplicates', [])
        )
        self._display_perpetual_state_alarms(
            "🤷‍♂️ Alarmas con Datos Insuficientes ( >24hs )",
            analysis_results.get('perpetual_insufficient_data', [])
        )
        self._display_perpetual_state_alarms(
            "📢 Alarmas 'Ruidosas' en Alarma Permanente ( >48hs )",
            analysis_results.get('perpetual_alarm', [])
        )

        st.divider()

        # --- Selection Processing and Script Generation ---
        selected_alarms = set()
        for key, value in st.session_state.items():
            if key.startswith("del_") and value:
                # Extract alarm name from key: "del_ALARM_NAME___CATEGORY_TITLE"
                alarm_name = key.split("___")[0].replace("del_", "", 1)
                selected_alarms.add(alarm_name)
        
        num_selected = len(selected_alarms)

        st.markdown("### 🗑️ Generación de Script de Eliminación")

        if num_selected > 25:
            st.warning(f"Puedes seleccionar hasta 25 alarmas por vez. Actualmente tienes {num_selected} seleccionadas.")
        else:
            st.info(f"Ha seleccionado {num_selected} alarma(s).")

        is_disabled = num_selected > 25 or num_selected == 0
        if st.button("Generar script de eliminación", disabled=is_disabled, use_container_width=True):
            if selected_alarms:
                quoted_alarm_names = [f'"{name}"' for name in selected_alarms]
                
                script_text = "#!/bin/bash\n"
                script_text += "# Script para eliminar las alarmas de CloudWatch seleccionadas.\n"
                script_text += "# Asegúrate de tener AWS CLI configurado con los permisos necesarios (cloudwatch:DeleteAlarms).\n\n"
                
                script_text += "aws cloudwatch delete-alarms --alarm-names "
                script_text += " ".join(quoted_alarm_names)
                
                st.success("Script generado con éxito. Cópialo y ejecútalo en tu terminal.")
                st.code(script_text, language='bash')

    def _display_orphan_alarms(self, title: str, alarms: List[Dict]):
        """Display alarms associated with terminated instances."""
        with st.expander(f"{title} ({len(alarms)})", expanded=True):
            if not alarms:
                st.success("No se encontraron alarmas asociadas a instancias terminadas.")
            else:
                st.warning("Las siguientes alarmas apuntan a una `InstanceId` que ya no existe. Son candidatas seguras para ser eliminadas.")
                for alarm in alarms:
                    alarm_name = alarm.get('AlarmName')
                    if not alarm_name: continue
                    
                    instance_id = next((d['Value'] for d in alarm.get('Dimensions', []) if d['Name'] == 'InstanceId'), 'N/A')
                    
                    cols = st.columns([1, 20])
                    with cols[0]:
                        st.checkbox(" ", key=f"del_{alarm_name}___{title}", label_visibility="hidden")
                    with cols[1]:
                        st.code(f"- {alarm_name}\n  (Apunta a la instancia terminada: {instance_id})", language=None)

    def _display_missing_dimension_alarms(self, title: str, alarms: List[Dict]):
        """Display alarms with no dimensions."""
        with st.expander(f"{title} ({len(alarms)})"):
            if not alarms:
                st.success("Todas las alarmas tienen dimensiones de asociación.")
            else:
                st.info("Las siguientes alarmas no tienen ninguna dimensión. No se pueden asociar a ningún recurso específico y podrían ser huérfanas. Requieren revisión manual.")
                for alarm in alarms:
                    alarm_name = alarm.get('AlarmName')
                    if not alarm_name: continue

                    cols = st.columns([1, 20])
                    with cols[0]:
                        st.checkbox(" ", key=f"del_{alarm_name}___{title}", label_visibility="hidden")
                    with cols[1]:
                        st.code(f"- {alarm_name}", language=None)

    def _display_duplicate_alarms(self, title: str, duplicate_groups: List[List[str]]):
        """Display groups of duplicate alarms."""
        with st.expander(f"{title} ({len(duplicate_groups)})"):
            if not duplicate_groups:
                st.success("No se encontraron alarmas duplicadas.")
            else:
                st.info("Los siguientes grupos de alarmas monitorean exactamente la misma métrica en el mismo recurso. Deberías conservar solo una de cada grupo.")
                for i, group in enumerate(duplicate_groups):
                    st.markdown(f"**Grupo {i+1}:**")
                    for alarm_name in group:
                        cols = st.columns([1, 20])
                        with cols[0]:
                            st.checkbox(" ", key=f"del_{alarm_name}___{title}_{i}", label_visibility="hidden")
                        with cols[1]:
                            st.code(f"- {alarm_name}", language=None)
                    st.divider()

    def _display_perpetual_state_alarms(self, title: str, alarms: List[Dict]):
        """Display alarms that have been in a specific state for a long time."""
        with st.expander(f"{title} ({len(alarms)})"):
            if not alarms:
                st.success("No se encontraron alarmas en este estado.")
            else:
                if "Insuficientes" in title:
                    st.info("Las siguientes alarmas llevan más de 24 horas sin recibir datos. Es probable que el recurso que monitorean ya no exista o que el agente de CloudWatch esté mal configurado.")
                if "Ruidosas" in title:
                    st.info("Las siguientes alarmas han estado en estado de ALARMA por más de 48 horas. Sus umbrales podrían ser demasiado bajos o incorrectos.")
                
                for alarm in alarms:
                    alarm_name = alarm.get('AlarmName')
                    if not alarm_name: continue

                    state_updated = alarm.get('StateUpdatedTimestamp').strftime('%Y-%m-%d %H:%M:%S')
                    
                    cols = st.columns([1, 20])
                    with cols[0]:
                        st.checkbox(" ", key=f"del_{alarm_name}___{title}", label_visibility="hidden")
                    with cols[1]:
                        st.code(f"- {alarm_name}\n  (En este estado desde: {state_updated})", language=None)
