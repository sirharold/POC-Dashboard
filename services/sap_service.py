"""
SAP Service class that wraps existing SAP functions without changing behavior.
"""
import streamlit as st
import time
import json
import re
import pandas as pd


class SAPService:
    """Manages SAP availability operations, wrapping existing functions."""
    
    def __init__(self, aws_service):
        """Initialize with AWS service dependency."""
        self.aws_service = aws_service

    def get_sap_availability_data(self, instance_id: str):
        """
        Get SAP availability data from CloudWatch Logs.
        The data is extracted by a Lambda function and stored in CloudWatch Logs.
        
        Returns a list of SAP services with their availability status.
        Exact same logic as original function.
        """
        try:
            # Get CloudWatch Logs client
            logs_client = self.aws_service.get_cross_account_boto3_client_cached('logs')
            if not logs_client:
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] Failed to get CloudWatch Logs client\n")
                return []
            
            # Get instance details to get the instance name
            details = self.aws_service.get_instance_details(instance_id)
            if not details:
                return []
            
            instance_name = next((tag['Value'] for tag in details.get('Tags', []) if tag['Key'] == 'Name'), '')
            
            # Determine environment based on instance name patterns
            # Production instances typically have 'PRD' in their names
            is_production = any(prod_pattern in instance_name.upper() 
                              for prod_pattern in ['PRD', 'PROD', 'PRODUCTION'])
            
            # CloudWatch Log Groups for SAP availability monitoring
            if is_production:
                possible_log_groups = [
                    '/aws/lambda/sap-availability-heartbeat-prod',
                    '/aws/lambda/sap-availability-heartbeat-prod-b'
                ]
            else:
                # QA/DEV environments
                possible_log_groups = [
                    '/aws/lambda/sap-availability-heartbeat',
                    '/aws/lambda/sap-availability-heartbeat-b'
                ]
            
            sap_services = []
            
            # Query CloudWatch Logs for SAP availability data
            for log_group in possible_log_groups:
                try:
                    # Query logs for the last 24 hours
                    end_time = int(time.time() * 1000)
                    start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago
                    
                    # Search for FILE_CHECK_DETAIL logs containing this instance_id
                    query = f'''
                    fields @timestamp, @message
                    | filter @message like /FILE_CHECK_DETAIL/
                    | filter @message like /{instance_id}/
                    | sort @timestamp desc
                    | limit 20
                    '''
                    
                    response = logs_client.start_query(
                        logGroupName=log_group,
                        startTime=start_time,
                        endTime=end_time,
                        queryString=query
                    )
                    
                    query_id = response['queryId']
                    
                    # Wait for query to complete
                    import time as time_module
                    time_module.sleep(2)  # Give query time to execute
                    
                    results_response = logs_client.get_query_results(queryId=query_id)
                    
                    if results_response['status'] == 'Complete' and results_response['results']:
                        # Parse the log results
                        parsed_services = self.parse_sap_log_results(results_response['results'], instance_id)
                        sap_services.extend(parsed_services)
                        
                        with open("/tmp/streamlit_aws_debug.log", "a") as f:
                            f.write(f"[{time.ctime()}] Found {len(parsed_services)} SAP services in {log_group} for {instance_name}\n")
                    
                except Exception as log_group_error:
                    # Log group might not exist, continue to next one
                    with open("/tmp/streamlit_aws_debug.log", "a") as f:
                        f.write(f"[{time.ctime()}] Log group {log_group} not accessible: {str(log_group_error)}\n")
                    continue
            
            # If no real data found, return placeholder data for demo
            if not sap_services:
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] No SAP data found in CloudWatch Logs for {instance_name}, using placeholder data\n")
                
                # Return placeholder data based on instance name patterns
                return self.get_placeholder_sap_data(instance_name)
            
            return sap_services
            
        except Exception as e:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Error getting SAP availability data from CloudWatch Logs: {str(e)}\n")
            return []

    def parse_sap_log_results(self, log_results, instance_id):
        """
        Parse CloudWatch Logs results to extract SAP availability data.
        
        Expected log format from Lambda:
        FILE_CHECK_DETAIL: {"vm_name": "...", "instance_id": "...", "file_path": "...", 
                          "status": "AVAILABLE/UNAVAILABLE", "details": "...", 
                          "raw_output": "...", "timestamp": "...", "environment": "..."}
        
        Exact same logic as original function.
        """
        services = {}
        
        for result in log_results:
            try:
                # Extract message from CloudWatch Logs result
                message = ""
                log_timestamp = ""
                
                for field in result:
                    if field['field'] == '@message':
                        message = field['value']
                    elif field['field'] == '@timestamp':
                        log_timestamp = field['value']
                
                if not message or 'FILE_CHECK_DETAIL:' not in message:
                    continue
                
                # Extract JSON from the FILE_CHECK_DETAIL log line
                # Pattern: FILE_CHECK_DETAIL: {"vm_name": ...}
                json_start = message.find('{')
                if json_start == -1:
                    continue
                    
                json_str = message[json_start:]
                
                # Parse the JSON data
                try:
                    sap_data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to fix common JSON issues (double quotes inside strings)
                    json_str = json_str.replace('""', '"')
                    try:
                        sap_data = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
                
                # Validate that this is for the correct instance
                if sap_data.get('instance_id') != instance_id:
                    continue
                
                # Extract service information from file path
                file_path = sap_data.get('file_path', '')
                # Example: /usr/sap/DAA/SMDA98/work/available.log -> DAA/SMDA98
                path_match = re.search(r'/usr/sap/([^/]+)/([^/]+)/', file_path)
                if path_match:
                    sap_system = path_match.group(1)
                    instance_num = path_match.group(2)
                    service_name = f"{sap_system} {instance_num}"
                else:
                    service_name = "Unknown SAP Service"
                
                status = sap_data.get('status', 'UNKNOWN')
                raw_output = sap_data.get('raw_output', '')
                details = sap_data.get('details', '')
                timestamp = sap_data.get('timestamp', log_timestamp)
                environment = sap_data.get('environment', 'UNKNOWN')
                vm_name = sap_data.get('vm_name', 'Unknown')
                
                # Create unique service key
                service_key = f"{vm_name}_{service_name}"
                
                # Only keep the most recent status for each service
                if service_key not in services or timestamp > services[service_key].get('timestamp', ''):
                    services[service_key] = {
                        'path': file_path,
                        'service': service_name,
                        'instance': vm_name,
                        'status': status,
                        'details': details,
                        'raw_output': raw_output,
                        'timestamp': timestamp,
                        'environment': environment,
                        'history': [{
                            'status': status,
                            'timestamp': timestamp,
                            'raw_output': raw_output
                        }]
                    }
                
            except Exception as parse_error:
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] Error parsing log result: {str(parse_error)}\n")
                continue
        
        return list(services.values())

    def get_placeholder_sap_data(self, instance_name):
        """Fallback placeholder data when no CloudWatch logs are found. Same as original function."""
        sap_services = []
        
        # Generate placeholder data based on instance name patterns
        if 'ERP' in instance_name.upper():
            sap_services.append({
                'path': '/usr/sap/ERP/DVEBMGS00/work/available.log',
                'service': 'SAP ERP',
                'instance': 'DVEBMGS00',
                'history': [
                    {'status': 'AVAILABLE', 'start_time': '2025-09-14 08:00:00', 'end_time': '2025-09-14 23:59:59'},
                    {'status': 'UNAVAILABLE', 'start_time': '2025-09-14 02:00:00', 'end_time': '2025-09-14 02:15:00'},
                ]
            })
        
        if 'CRM' in instance_name.upper():
            sap_services.append({
                'path': '/usr/sap/CRM/DVEBMGS01/work/available.log',
                'service': 'SAP CRM',
                'instance': 'DVEBMGS01',
                'history': [
                    {'status': 'AVAILABLE', 'start_time': '2025-09-14 00:00:00', 'end_time': '2025-09-14 23:59:59'},
                ]
            })
        
        return sap_services

    def create_sap_availability_table(self, sap_data):
        """Create a table showing SAP availability data. Exact same logic as original function."""
        if not sap_data:
            return st.info("No se encontraron servicios SAP para esta instancia.")
        
        st.markdown("## 🔧 Disponibilidad Servicios SAP")
        
        for service in sap_data:
            st.markdown(f"### {service['service']} ({service['instance']})")
            st.markdown(f"**Path:** `{service['path']}`")
            
            # Get current status from the service data
            current_status = service.get('status', 'UNKNOWN')
            status_color = "🟢" if current_status == 'AVAILABLE' else "🔴" if current_status == 'UNAVAILABLE' else "⚫"
            st.markdown(f"**Estado Actual:** {status_color} {current_status}")
            
            # Show additional details if available
            if service.get('details'):
                st.markdown(f"**Detalles:** {service['details']}")
            
            # Show raw output from SAP logs
            if service.get('raw_output'):
                with st.expander("Ver salida completa del log"):
                    st.code(service['raw_output'])
            
            # Show environment and timestamp
            if service.get('environment'):
                st.markdown(f"**Ambiente:** {service['environment']}")
            
            if service.get('timestamp'):
                st.markdown(f"**Última verificación:** {service['timestamp']}")
            
            # Create DataFrame for history if available
            if service.get('history'):
                df_data = []
                for i, entry in enumerate(service['history'][:10]):  # Show max 10 entries
                    df_data.append({
                        '#': i + 1,
                        'Estado': '🟢 DISPONIBLE' if entry['status'] == 'AVAILABLE' else '🔴 NO DISPONIBLE',
                        'Timestamp': entry.get('timestamp', 'N/A'),
                        'Salida': entry.get('raw_output', 'N/A')[:50] + '...' if len(entry.get('raw_output', '')) > 50 else entry.get('raw_output', 'N/A')
                    })
                
                if df_data:
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos de historial disponibles")
            
            st.markdown("---")

    def get_available_log_content(self, instance_id: str):
        """
        Get available.log content from CloudWatch Logs for SAP availability monitoring.
        Returns the raw log content or None if not available.
        """
        try:
            # Get CloudWatch Logs client
            logs_client = self.aws_service.get_cross_account_boto3_client_cached('logs')
            if not logs_client:
                return None
            
            # Get instance details to get the instance name
            details = self.aws_service.get_instance_details(instance_id)
            if not details:
                return None
            
            instance_name = next((tag['Value'] for tag in details.get('Tags', []) if tag['Key'] == 'Name'), '')
            
            # Determine environment based on instance name patterns
            is_production = any(prod_pattern in instance_name.upper() 
                              for prod_pattern in ['PRD', 'PROD', 'PRODUCTION'])
            
            # CloudWatch Log Groups for SAP availability monitoring
            if is_production:
                possible_log_groups = [
                    '/aws/lambda/sap-availability-heartbeat-prod',
                    '/aws/lambda/sap-availability-prod'
                ]
            else:
                possible_log_groups = [
                    '/aws/lambda/sap-availability-heartbeat-qa',
                    '/aws/lambda/sap-availability-qa',
                    '/aws/lambda/sap-availability-heartbeat-dev',
                    '/aws/lambda/sap-availability-dev'
                ]
            
            # Try each log group to find available.log content
            for log_group_name in possible_log_groups:
                try:
                    # Get recent log streams
                    streams_response = logs_client.describe_log_streams(
                        logGroupName=log_group_name,
                        orderBy='LastEventTime',
                        descending=True,
                        limit=10
                    )
                    
                    # Search through recent log streams for available.log content
                    for stream in streams_response.get('logStreams', []):
                        events_response = logs_client.get_log_events(
                            logGroupName=log_group_name,
                            logStreamName=stream['logStreamName'],
                            limit=100
                        )
                        
                        # Look for available.log content in log events
                        for event in events_response.get('events', []):
                            message = event.get('message', '')
                            
                            # Check if this log event contains available.log content for our server
                            if ('available.log' in message.lower() and 
                                instance_name.lower() in message.lower()):
                                return message
                                
                except Exception as e:
                    # Continue to next log group if this one fails
                    continue
            
            return None
            
        except Exception as e:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Error getting available.log content: {e}\n")
            return None