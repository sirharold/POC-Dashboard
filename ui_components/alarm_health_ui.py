
"""
UI component for the Alarm Health Analysis page.
"""
import streamlit as st
from typing import Dict, List

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

        with st.spinner("Ejecutando análisis... Esto puede tardar uno o dos minutos."):
            analysis_results = self.aws_service.analyze_alarm_health()

        if not analysis_results or 'error' in analysis_results:
            st.error(f"No se pudo completar el análisis de alarmas. Error: {analysis_results.get('error', 'Uknown')}")
            return

        # --- Render Results ---
        self._display_orphan_alarms(analysis_results.get('orphan_by_terminated_instance', []))
        self._display_missing_dimension_alarms(analysis_results.get('orphan_by_missing_dimension', []))
        self._display_duplicate_alarms(analysis_results.get('duplicates', []))
        self._display_perpetual_state_alarms(
            "☽️ Alarmas con Datos Insuficientes ( >24hs )",
            analysis_results.get('perpetual_insufficient_data', [])
        )
        self._display_perpetual_state_alarms(
            "📢 Alarmas 'Ruidosas' en Alarma Permanente ( >48hs )",
            analysis_results.get('perpetual_alarm', [])
        )

    def _display_orphan_alarms(self, alarms: List[Dict]):
        """Display alarms associated with terminated instances."""
        with st.expander(f"🚨 Alarmas Huérfanas por Instancia Terminada ({len(alarms)})", expanded=True):
            if not alarms:
                st.success("No se encontraron alarmas asociadas a instancias terminadas.")
            else:
                st.warning("Las siguientes alarmas apuntan a una `InstanceId` que ya no existe. Son candidatas seguras para ser eliminadas.")
                for alarm in alarms:
                    instance_id = next((d['Value'] for d in alarm.get('Dimensions', []) if d['Name'] == 'InstanceId'), 'N/A')
                    st.code(f"- {alarm.get('AlarmName')}\n  (Apunta a la instancia terminada: {instance_id})", language=None)

    def _display_missing_dimension_alarms(self, alarms: List[Dict]):
        """Display alarms with no dimensions."""
        with st.expander(f"❓ Alarmas Sin Asociación Clara ({len(alarms)})"):
            if not alarms:
                st.success("Todas las alarmas tienen dimensiones de asociación.")
            else:
                st.info("Las siguientes alarmas no tienen ninguna dimensión. No se pueden asociar a ningùn recurso específico y podrían ser huérfanas. Requieren revisión manual.")
                for alarm in alarms:
                    st.code(f"- {alarm.get('AlarmName')}", language=None)

    def _display_duplicate_alarms(self, duplicate_groups: List[List[str]]):
        """Display groups of duplicate alarms."""
        with st.expander(f"👯‍♀️ Grupos de Alarmas Duplicadas ({len(duplicate_groups)})"):
            if not duplicate_groups:
                st.success("No se encontraron alarmas duplicadas.")
            else:
                st.info("Los siguientes grupos de alarmas monitorean exactamente la misma métrica en el mismo recurso. Deberías conservar solo una de cada grupo.")
                for i, group in enumerate(duplicate_groups):
                    st.markdown(f"**Grupo {i+1}:**")
                    for alarm_name in group:
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
                    state_updated = alarm.get('StateUpdatedTimestamp').strftime('%Y-%m-%d %H:%M:%S')
                    st.code(f"- {alarm.get('AlarmName')}\n  (En este estado desde: {state_updated})", language=None)
