"""
Monthly Report UI component for historical alarm and metrics reporting.
"""
import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd
from utils.availability_calculator import AvailabilityCalculator
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors


class MonthlyReportUI:
    """UI component for the monthly report page."""

    def __init__(self, aws_service):
        """Initialize the monthly report UI with AWS service."""
        self.aws_service = aws_service

    def _get_available_months(self):
        """
        Get list of available months starting from September 2025 up to current month.
        Returns list of tuples: (display_name, start_date, end_date)
        """
        # Start month: September 2025
        start_year = 2025
        start_month = 9

        # Current date
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Generate list of months from September 2025 to current month
        months = []
        year = start_year
        month = start_month

        while (year < current_year) or (year == current_year and month <= current_month):
            # Create date for first day of month
            month_date = datetime(year, month, 1)

            # Calculate last day of month
            if month == 12:
                next_month_date = datetime(year + 1, 1, 1)
            else:
                next_month_date = datetime(year, month + 1, 1)

            last_day = next_month_date - timedelta(days=1)

            # Format display name: "Octubre 2025", "Noviembre 2025"
            month_names = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }

            display_name = f"{month_names[month]} {year}"

            months.append((display_name, month_date.date(), last_day.date()))

            # Move to next month
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1

        # Reverse to show most recent months first
        months.reverse()

        return months

    def _get_current_month_dates(self):
        """Get first day of current month and today's date."""
        now = datetime.now()
        first_day = datetime(now.year, now.month, 1).date()
        today = now.date()
        return first_day, today

    def display_monthly_report(self):
        """Display the monthly report page."""
        # Add back to dashboard link
        columns_param = st.query_params.get('columns', '2')
        if st.button("← Volver al Dashboard", type="secondary"):
            # Clear monthly_report query param and preserve columns
            st.query_params.clear()
            st.query_params.update({"columns": columns_param})
            st.rerun()

        st.markdown("# 📅 Informe Mensual")

        # Get available months
        available_months = self._get_available_months()

        # Initialize session state for dates if not exists
        if 'monthly_report_start_date' not in st.session_state:
            first_day, today = self._get_current_month_dates()
            st.session_state.monthly_report_start_date = first_day
            st.session_state.monthly_report_end_date = today
            st.session_state.selected_month_index = 0  # "Personalizado"
            st.session_state.date_widget_key = 0  # Key to force widget recreation

        # Metric type selector
        col_metric = st.columns([2, 6])
        with col_metric[0]:
            metric_type = st.selectbox(
                "Tipo de métrica:",
                options=["Ping", "Availability", "Availability Percentage"],
                index=0,
                key="metric_type_selector"
            )

        st.markdown("---")

        # Month selector dropdown and date pickers in compact layout
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            # Dropdown with month options
            month_options = ["Personalizado"] + [m[0] for m in available_months]
            selected_month_index = st.selectbox(
                "Seleccionar mes:",
                options=range(len(month_options)),
                format_func=lambda x: month_options[x],
                index=st.session_state.selected_month_index,
                key="month_selector"
            )

            # Update dates when month is selected (and it's different from last selection)
            if selected_month_index != st.session_state.selected_month_index:
                st.session_state.selected_month_index = selected_month_index

                if selected_month_index > 0:  # Not "Personalizado"
                    # Get the month data (index - 1 because "Personalizado" is at index 0)
                    month_data = available_months[selected_month_index - 1]
                    st.session_state.monthly_report_start_date = month_data[1]
                    st.session_state.monthly_report_end_date = month_data[2]
                    # Change widget key to force recreation with new dates
                    st.session_state.date_widget_key += 1
                    st.rerun()  # Force rerun to update date pickers

        with col2:
            start_date = st.date_input(
                "Fecha de inicio:",
                value=st.session_state.monthly_report_start_date,
                key=f"start_date_picker_{st.session_state.date_widget_key}"
            )

        with col3:
            end_date = st.date_input(
                "Fecha de término:",
                value=st.session_state.monthly_report_end_date,
                key=f"end_date_picker_{st.session_state.date_widget_key}"
            )

        with col4:
            # Add some spacing to align button vertically
            st.markdown("<div style='margin-top: 1.9rem;'></div>", unsafe_allow_html=True)
            consultar_clicked = st.button("🔍 Consultar", use_container_width=True, type="primary")

        # Check if dates were manually changed (different from session state)
        dates_changed_manually = (
            start_date != st.session_state.monthly_report_start_date or
            end_date != st.session_state.monthly_report_end_date
        )

        # If dates were changed manually and we're not on "Personalizado", switch to it
        if dates_changed_manually and st.session_state.selected_month_index != 0:
            st.session_state.selected_month_index = 0
            st.session_state.monthly_report_start_date = start_date
            st.session_state.monthly_report_end_date = end_date
            st.session_state.date_widget_key += 1
            st.rerun()

        # Update session state with current picker values only if not changed manually
        # (to avoid triggering rerun when just loading the page)
        if not dates_changed_manually:
            st.session_state.monthly_report_start_date = start_date
            st.session_state.monthly_report_end_date = end_date
        else:
            # Dates changed, update session state without rerun if already on "Personalizado"
            st.session_state.monthly_report_start_date = start_date
            st.session_state.monthly_report_end_date = end_date

        # Show selected period info in compact format
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fecha Inicio", start_date.strftime("%d/%m/%Y"))
        with col2:
            st.metric("Fecha Término", end_date.strftime("%d/%m/%Y"))
        with col3:
            # Calculate number of days
            days_diff = (end_date - start_date).days + 1
            st.metric("Días", days_diff)

        st.divider()

        # Process query if button was clicked
        if consultar_clicked:
            # Validate dates
            if start_date > end_date:
                st.error("La fecha de inicio debe ser anterior a la fecha de término.")
            else:
                # Process based on metric type
                if metric_type == "Ping":
                    self._display_ping_metrics(start_date, end_date)
                elif metric_type == "Availability":
                    st.info("Funcionalidad de Availability en desarrollo...")
                elif metric_type == "Availability Percentage":
                    st.info("Funcionalidad de Availability Percentage en desarrollo...")

    def _get_instance_data_by_name(self, instance_name):
        """Get instance ID and Schedule tag from instance name."""
        try:
            # Get all instances data (cached)
            instances_data = self.aws_service.get_aws_data()

            # Find instance by name
            for instance in instances_data:
                if instance.get('Name') == instance_name:
                    return {
                        'ID': instance.get('ID'),
                        'Name': instance.get('Name'),
                        'Schedule': instance.get('Schedule', None)  # Case sensitive
                    }

            return None
        except Exception as e:
            st.error(f"Error buscando instancia: {str(e)}")
            return None

    def _get_instances_by_environment(self, environment):
        """Get all instances for a specific environment."""
        try:
            # Get all instances data (cached)
            instances_data = self.aws_service.get_aws_data()

            # Filter instances by environment
            env_instances = []
            for instance in instances_data:
                if instance.get('Environment', '').upper() == environment.upper():
                    env_instances.append({
                        'ID': instance.get('ID'),
                        'Name': instance.get('Name'),
                        'Schedule': instance.get('Schedule', None)
                    })

            return env_instances
        except Exception as e:
            st.error(f"Error obteniendo instancias de {environment}: {str(e)}")
            return []

    def _get_ping_metric_with_dimensions(self, instance_id, instance_name, start_time, end_time, period):
        """
        Get PingReachable metric using both InstanceId and Name dimensions.

        The EC2/ICMPHealthcheck namespace requires BOTH dimensions.
        """
        try:
            # Get CloudWatch client
            cloudwatch = self.aws_service.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch:
                return pd.DataFrame()

            # Query with BOTH dimensions
            response = cloudwatch.get_metric_statistics(
                Namespace='EC2/ICMPHealthcheck',
                MetricName='PingReachable',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id},
                    {'Name': 'Name', 'Value': instance_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Maximum']
            )

            if not response['Datapoints']:
                return pd.DataFrame()

            # Convert to DataFrame and sort
            df = pd.DataFrame(response['Datapoints'])
            df = df.sort_values(by='Timestamp').reset_index(drop=True)
            return df

        except Exception as e:
            st.error(f"Error obteniendo métrica PingReachable: {str(e)}")
            return pd.DataFrame()

    def _calculate_optimal_period(self, start_date, end_date):
        """
        Calculate optimal period to avoid CloudWatch 1440 datapoints limit.

        CloudWatch limits: max 1440 datapoints per request.
        Formula: period = total_seconds / 1440

        Minimum period is 60 seconds (1 minute).
        """
        # Calculate total seconds in the date range
        total_seconds = (end_date - start_date).total_seconds()

        # Calculate minimum period to stay under 1440 datapoints
        min_period = total_seconds / 1440

        # Round up to nearest minute (60 seconds minimum)
        period = max(60, int(min_period / 60) * 60)

        # CloudWatch accepts periods: 60, 300 (5min), 900 (15min), 3600 (1hr), 86400 (1day)
        # Round to next valid period
        valid_periods = [60, 300, 900, 3600, 21600, 86400]  # 1min, 5min, 15min, 1hr, 6hr, 1day
        period = next((p for p in valid_periods if p >= period), 86400)

        return period

    def _generate_pdf_report(self, charts_data, start_date, end_date):
        """
        Generate PDF report with charts in landscape format.

        Args:
            charts_data: List of tuples (instance_name, availability_percentage, fig)
            start_date: Report start date
            end_date: Report end date

        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        # Use landscape orientation for 4 columns
        from reportlab.lib.pagesizes import landscape
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        story = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#000000'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        # Title
        title_text = f"Métricas de Ping Desde {start_date.strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}"
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Convert charts to images and add to PDF
        # Organize in 4 columns (same as UI)
        chart_images = []

        for instance_name, availability_percentage, fig in charts_data:
            # Convert plotly figure to image bytes
            img_bytes = fig.to_image(format="png", width=300, height=250)
            img = Image(BytesIO(img_bytes), width=2.4*inch, height=2*inch)
            chart_images.append(img)

        # Create table with 4 columns (landscape orientation)
        if chart_images:
            # Pad with empty cells if needed to complete the row
            while len(chart_images) % 4 != 0:
                chart_images.append(Paragraph("", styles['Normal']))

            # Create rows of 4 charts each
            rows = []
            for i in range(0, len(chart_images), 4):
                rows.append(chart_images[i:i+4])

            # Column widths for 4 columns in landscape letter (11 x 8.5 inches)
            # Total width available: ~10 inches (leaving margins)
            table = Table(rows, colWidths=[2.5*inch, 2.5*inch, 2.5*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(table)

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def _display_ping_metrics(self, start_date, end_date):
        """Display ping metrics for the selected period organized by environment."""
        # Title and PDF button in same row
        title_col, button_col = st.columns([6, 1])

        with title_col:
            title_text = f"Métricas de Ping Desde {start_date.strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}"
            st.markdown(f"### {title_text}")

        # We'll store chart data for PDF generation (all environments)
        all_charts_data = []

        # Convert dates to datetime objects with time
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Calculate optimal period once (same for all instances)
        period = self._calculate_optimal_period(start_datetime, end_datetime)

        # Process each environment in order: Production, QA, DEV
        environments = [
            ('Production', 'Producción'),
            ('QA', 'QA'),
            ('DEV', 'Desarrollo')
        ]

        for env_tag, env_display_name in environments:
            # Get instances for this environment
            with st.spinner(f"Obteniendo servidores de {env_display_name}..."):
                env_instances = self._get_instances_by_environment(env_tag)

            # Skip if no instances found
            if not env_instances:
                continue

            # Display section subtitle
            st.markdown(f"#### {env_display_name} ({len(env_instances)} servidor{'es' if len(env_instances) > 1 else ''})")

            # Store charts for this environment section
            section_charts_data = []

            # Process each instance in this environment
            for idx, instance_data in enumerate(env_instances):
                instance_id = instance_data['ID']
                instance_name = instance_data['Name']
                schedule_tag = instance_data['Schedule']

                with st.spinner(f"Obteniendo datos de {instance_name}..."):
                    # Get metric data from CloudWatch using BOTH dimensions
                    df = self._get_ping_metric_with_dimensions(
                        instance_id=instance_id,
                        instance_name=instance_name,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        period=period
                    )

                    if df.empty:
                        st.warning(f"⚠️ Sin datos de ping para {instance_name}")
                        continue

                    # Calculate availability using the AvailabilityCalculator
                    stat_column = 'Maximum' if 'Maximum' in df.columns else 'Average'
                    availability_stats = AvailabilityCalculator.calculate_availability(
                        df=df,
                        schedule_tag=schedule_tag,
                        value_column=stat_column
                    )

                    # Use scheduled availability percentage (excludes scheduled downtime)
                    availability_percentage = availability_stats['scheduled_availability_percentage']

                    # Format title string (avoiding potential f-string issues with %)
                    chart_title = "{} - Disp: {:.1f}%".format(instance_name, availability_percentage)

                    # Create plotly line chart
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=df['Timestamp'],
                        y=df[stat_column],
                        mode='lines+markers',
                        name='Ping Status',
                        line=dict(color='#1f77b4', width=2),
                        marker=dict(size=4),
                        hovertemplate='<b>Fecha:</b> %{x|%d/%m/%Y %H:%M}<br><b>Estado:</b> %{y}<extra></extra>'
                    ))

                    # Configure layout for binary data (0 or 1)
                    fig.update_layout(
                        title=dict(
                            text=chart_title,
                            x=0.5,
                            xanchor='center',
                            font=dict(size=16, family='Arial, sans-serif', color='black')
                        ),
                        height=300,
                        margin=dict(l=30, r=20, t=50, b=40),
                        xaxis=dict(
                            title="",
                            gridcolor='lightgray',
                            showgrid=True
                        ),
                        yaxis=dict(
                            title="",
                            gridcolor='lightgray',
                            showgrid=True,
                            tickmode='array',
                            tickvals=[0, 1],
                            ticktext=['0', '1'],
                            range=[-0.1, 1.1]
                        ),
                        hovermode='x unified',
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )

                    # Store chart data for this section
                    section_charts_data.append((instance_name, availability_percentage, fig))

            # Display charts for this environment in a 4-column grid
            if section_charts_data:
                num_charts = len(section_charts_data)
                cols_per_row = 4

                # Create rows with 4 columns each
                for row_start in range(0, num_charts, cols_per_row):
                    cols = st.columns(cols_per_row)
                    row_charts = section_charts_data[row_start:row_start + cols_per_row]

                    for col_idx, (inst_name, avail_pct, chart_fig) in enumerate(row_charts):
                        with cols[col_idx]:
                            st.plotly_chart(chart_fig, use_container_width=True)

                # Add all section charts to the global list for PDF
                all_charts_data.extend(section_charts_data)

                # Add spacing between environment sections
                st.markdown("---")

        # Add PDF download button after all charts are displayed
        with button_col:
            # Add some vertical spacing to align with title
            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

            if all_charts_data:
                # Generate PDF with all environments
                pdf_buffer = self._generate_pdf_report(all_charts_data, start_date, end_date)

                # Create filename with dates
                filename = f"Ping_Report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

                # Download button
                st.download_button(
                    label="📄 PDF",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
