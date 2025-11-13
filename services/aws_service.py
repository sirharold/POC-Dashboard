"""
AWS Service class that wraps existing AWS functions without changing behavior.
"""
import streamlit as st
import boto3
import time
from collections import Counter
from botocore.exceptions import ClientError
import pandas as pd
import datetime


class AWSService:
    """Manages all AWS operations, wrapping existing functions."""
    
    def __init__(self):
        """Initialize AWS Service."""
        self.role_arn = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"
    
    @st.cache_resource(ttl=60)  # 1 minute cache for good balance between performance and freshness
    def get_cross_account_boto3_client(_self, service_name: str):
        """
        Asume el rol de la cuenta cliente y retorna un cliente de boto3 para el servicio especificado.
        This is the exact same function as the original, just wrapped in a class.
        """
        try:
            sts_client = boto3.client('sts')
            response = sts_client.assume_role(
                RoleArn=_self.role_arn,
                RoleSessionName='StreamlitDashboardSession'
            )
            
            credentials = response['Credentials']
            
            return boto3.client(
                service_name,
                region_name='us-east-1',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
            )
        except ClientError as e:
            return None

    def get_cross_account_boto3_client_cached(self, service_name: str):
        """Cached version of the client getter."""
        return self.get_cross_account_boto3_client(service_name)
    
    def clear_cache(self):
        """Clear the AWS client cache to force fresh data fetch."""
        self.get_cross_account_boto3_client.clear()

    def test_aws_connection(self):
        """
        Attempts to assume the role and create a simple STS client to test AWS connectivity.
        Returns a tuple (status_message, error_details).
        Exact same logic as original function.
        """
        try:
            sts_client = boto3.client('sts')
            response = sts_client.assume_role(
                RoleArn=self.role_arn,
                RoleSessionName='StreamlitConnectionTestSession'
            )
            # If assume_role succeeds, we can try to get a client
            credentials = response['Credentials']
            boto3.client(
                'ec2',
                region_name='us-east-1',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
            )
            return "Conexión AWS OK", None
        except ClientError as e:
            return "Error de Conexión AWS", str(e)
        except Exception as e:
            return "Error Inesperado de Conexión AWS", str(e)

    def get_aws_data(self):
        """
        Fetch EC2 instances and their CloudWatch alarms from AWS.
        Returns a list of instance dictionaries with their state and alarms.
        Exact same logic as original function.
        """
        instances_data = []
        
        try:
            # Log the start of data fetching
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Starting get_aws_data()\n")
            
            # Get EC2 client
            ec2 = self.get_cross_account_boto3_client_cached('ec2')
            if not ec2:
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] Failed to get EC2 client\n")
                return []
            
            # Get CloudWatch client
            cloudwatch = self.get_cross_account_boto3_client_cached('cloudwatch')
            if not cloudwatch:
                with open("/tmp/streamlit_aws_debug.log", "a") as f:
                    f.write(f"[{time.ctime()}] Failed to get CloudWatch client\n")
                return []
            
            # Fetch all EC2 instances
            response = ec2.describe_instances()
            
            # Get all CloudWatch alarms ONCE (more efficient)
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Getting all CloudWatch alarms...\n")
            
            alarm_paginator = cloudwatch.get_paginator('describe_alarms')
            all_alarms = []
            for page in alarm_paginator.paginate():
                all_alarms.extend(page['MetricAlarms'])
            
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Retrieved {len(all_alarms)} total alarms\n")
            
            # Process each instance
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance.get('InstanceId', '')
                    instance_state = instance.get('State', {}).get('Name', 'unknown')
                    
                    # Extract tags
                    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                    
                    # Only include instances with DashboardGroup tag
                    if 'DashboardGroup' not in tags:
                        continue
                    
                    with open("/tmp/streamlit_aws_debug.log", "a") as f:
                        f.write(f"[{time.ctime()}] Processing instance {instance_id} ({tags.get('Name', 'NoName')})\n")
                    
                    # Count alarms for this instance
                    instance_alarms = Counter()
                    alarms_list_for_instance = [] # Store full alarm objects
                    instance_name = tags.get('Name', instance_id)
                    
                    for alarm in all_alarms:
                        dimensions = alarm.get('Dimensions', [])
                        alarm_name = alarm.get('AlarmName', '')
                        
                        # Check if alarm belongs to this instance using dimension-based matching
                        belongs_to_instance = (
                            # 1. InstanceId dimension (most reliable - covers 778/841 alarms)
                            any(d['Name'] == 'InstanceId' and d['Value'] == instance_id for d in dimensions) or

                            # 2. Server dimension for SSM/Composite alarms (covers remaining 63/841 alarms)
                            any(d['Name'] == 'Server' and d['Value'].upper() == instance_name.upper() for d in dimensions)
                        )
                        
                        if belongs_to_instance:
                            alarms_list_for_instance.append(alarm) # Add the full object
                            alarm_state = alarm.get('StateValue', 'UNKNOWN')
                            
                            # Log each alarm for debugging
                            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                                f.write(f"[{time.ctime()}] Alarm: {alarm_name}, State: {alarm_state}, Instance: {instance_id}\n")
                            
                            # Check if this is a preventive alarm
                            if alarm_state == 'ALARM' and ('ALERTA' in alarm_name.upper() or 'PROACTIVA' in alarm_name.upper() or 'PREVENTIVA' in alarm_name.upper() or 'SMDA98' in alarm_name.upper()):
                                instance_alarms['PREVENTIVE'] += 1
                            else:
                                instance_alarms[alarm_state] += 1
                    
                    with open("/tmp/streamlit_aws_debug.log", "a") as f:
                        f.write(f"[{time.ctime()}] Instance {instance_id} has {len(instance_alarms)} alarm states: {dict(instance_alarms)}\n")
                    
                    # Create instance data structure
                    # Clean DashboardGroup value to remove extra whitespace
                    dashboard_group = tags.get('DashboardGroup', 'Uncategorized').strip()
                    
                    # Get the actual number of attached EBS volumes, ignoring other block devices.
                    ebs_volumes = [
                        mapping for mapping in instance.get('BlockDeviceMappings', [])
                        if 'Ebs' in mapping
                    ]
                    disk_count = len(ebs_volumes)

                    instance_data = {
                        'ID': instance_id,
                        'Name': tags.get('Name', instance_id),
                        'State': instance_state,
                        'Environment': tags.get('Environment', 'Unknown'),
                        'DashboardGroup': dashboard_group,
                        'Alarms': instance_alarms,
                        'AlarmsList': [], # Placeholder, as alarms_list is not defined here
                        'OperatingSystem': instance.get('PlatformDetails', 'Linux/UNIX'),
                        'PrivateIP': instance.get('PrivateIpAddress', 'N/A'),
                        'DiskCount': disk_count,
                        'AlarmObjects': alarms_list_for_instance,
                        'Schedule': tags.get('Schedule', None)  # For availability calculations (case sensitive)
                    }
                    
                    
                    instances_data.append(instance_data)
            
            # Log the results
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Found {len(instances_data)} instances with DashboardGroup tag\n")
                f.write(f"[{time.ctime()}] Total alarms processed: {len(all_alarms)}\n")
            
            return instances_data
            
        except Exception as e:
            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                f.write(f"[{time.ctime()}] Error in get_aws_data(): {str(e)}\n")
            return []

    def get_instance_details(self, instance_id: str):
        """Get detailed information for a specific instance. Same as original function."""
        try:
            ec2 = self.get_cross_account_boto3_client('ec2')
            if not ec2: 
                return None
            response = ec2.describe_instances(InstanceIds=[instance_id])
            if response['Reservations'] and response['Reservations'][0]['Instances']:
                return response['Reservations'][0]['Instances'][0]
            return None
        except Exception as e:
            st.error(f"Error getting instance details: {e}")
            return None

    def get_volume_details(self, block_device_mappings: list) -> dict:
        """Get detailed information for EBS volumes from block device mappings."""
        volume_details = {}
        volume_ids = [device['Ebs']['VolumeId'] for device in block_device_mappings if 'Ebs' in device]

        if not volume_ids:
            return volume_details

        try:
            ec2 = self.get_cross_account_boto3_client('ec2')
            if not ec2: return {}
            
            response = ec2.describe_volumes(VolumeIds=volume_ids)
            
            for volume in response.get('Volumes', []):
                tags = {tag['Key']: tag['Value'] for tag in volume.get('Tags', [])}
                volume_details[volume['VolumeId']] = {
                    'Size': volume.get('Size'),
                    'Iops': volume.get('Iops'),
                    'Tags': tags,
                    'VolumeType': volume.get('VolumeType')
                }
            return volume_details
        except Exception as e:
            st.error(f"Error getting volume details: {e}")
            return {}

    def get_metric_history(self, instance_id: str, metric_name: str, namespace: str, statistic: str = 'Average', hours: int = 3) -> pd.DataFrame:
        """Get time-series data for a specific CloudWatch metric."""
        try:
            cloudwatch = self.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch: return pd.DataFrame()

            response = cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.datetime.utcnow() - datetime.timedelta(hours=hours),
                EndTime=datetime.datetime.utcnow(),
                Period=300,  # 5-minute intervals
                Statistics=[statistic]
            )

            if not response['Datapoints']:
                return pd.DataFrame()

            # Convert to DataFrame and sort
            df = pd.DataFrame(response['Datapoints'])
            df = df.sort_values(by='Timestamp').reset_index(drop=True)
            return df

        except Exception as e:
            # Don't show error for metrics that might not exist
            # st.warning(f"Could not retrieve metric {metric_name}: {e}")
            return pd.DataFrame()

    def get_metric_history_by_name(self, instance_name: str, metric_name: str, namespace: str,
                                     start_time: datetime.datetime, end_time: datetime.datetime,
                                     statistic: str = 'Average', period: int = 300) -> pd.DataFrame:
        """
        Get time-series data for a specific CloudWatch metric using instance name.

        Args:
            instance_name: Name of the instance (e.g., 'SRVERPQA')
            metric_name: CloudWatch metric name (e.g., 'PingReachable')
            namespace: CloudWatch namespace (e.g., 'CWAgent')
            start_time: Start time for the query
            end_time: End time for the query
            statistic: Statistic to retrieve (Average, Sum, Maximum, etc.)
            period: Period in seconds (default 300 = 5 minutes)

        Returns:
            DataFrame with Timestamp and metric values
        """
        try:
            cloudwatch = self.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch:
                return pd.DataFrame()

            response = cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=[{'Name': 'Name', 'Value': instance_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic]
            )

            if not response['Datapoints']:
                return pd.DataFrame()

            # Convert to DataFrame and sort
            df = pd.DataFrame(response['Datapoints'])
            df = df.sort_values(by='Timestamp').reset_index(drop=True)
            return df

        except Exception as e:
            st.error(f"Error obteniendo métrica {metric_name} para {instance_name}: {str(e)}")
            return pd.DataFrame()

    def get_availability_metrics_for_instance(self, instance_id: str, environment: str) -> list:
        """
        Get all availability heartbeat metrics for an instance.

        Args:
            instance_id: EC2 Instance ID (e.g., 'i-05b2454bb08ed6c8f')
            environment: Environment tag value ('Production', 'QA', 'DEV')

        Returns:
            List of metric dictionaries with MetricName and Dimensions
        """
        try:
            cloudwatch = self.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch:
                return []

            # Determine namespace based on environment
            if environment and environment.upper() == 'PRODUCTION':
                namespace = 'SAP_Monitoring_Availability_Prod'
            else:
                namespace = 'SAP_Monitoring_Availability'

            # List all metrics in the namespace filtered by InstanceId
            paginator = cloudwatch.get_paginator('list_metrics')
            page_iterator = paginator.paginate(
                Namespace=namespace,
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
            )

            metrics = []
            for page in page_iterator:
                for metric in page['Metrics']:
                    if 'heartbeat' in metric['MetricName'].lower():
                        metrics.append(metric)

            return metrics

        except Exception as e:
            return []

    def get_availability_metric_data(self, namespace: str, metric_name: str, dimensions: list,
                                       start_time: datetime.datetime, end_time: datetime.datetime,
                                       period: int = 900) -> pd.DataFrame:
        """
        Get availability metric data with dimensions.

        Args:
            namespace: CloudWatch namespace
            metric_name: Metric name (e.g., 'SRVERPQA_ERQ_ASCS01_heartbeat')
            dimensions: List of dimension dicts [{'Name': 'VMName', 'Value': '...'}, ...]
            start_time: Start datetime
            end_time: End datetime
            period: Period in seconds (default 900 = 15 minutes)

        Returns:
            DataFrame with Timestamp and metric values
        """
        try:
            cloudwatch = self.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch:
                return pd.DataFrame()

            response = cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average', 'Minimum', 'Maximum']
            )

            if not response['Datapoints']:
                return pd.DataFrame()

            # Convert to DataFrame and sort
            df = pd.DataFrame(response['Datapoints'])
            df = df.sort_values(by='Timestamp').reset_index(drop=True)
            return df

        except Exception as e:
            return pd.DataFrame()

    def get_alarms_for_instance(self, instance_id: str):
        """Get CloudWatch alarms for an instance, including SAP alarms by name matching."""
        try:
            cloudwatch = self.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch: 
                return []
            
            # Get instance name for SAP alarm matching
            ec2 = self.get_cross_account_boto3_client('ec2')
            instance_name = instance_id  # Default fallback
            if ec2:
                try:
                    response = ec2.describe_instances(InstanceIds=[instance_id])
                    for reservation in response['Reservations']:
                        for instance in reservation['Instances']:
                            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                            if 'Name' in tags:
                                instance_name = tags['Name']
                                break
                except:
                    pass  # Keep using instance_id as fallback
            
            paginator = cloudwatch.get_paginator('describe_alarms')
            pages = paginator.paginate()
            instance_alarms = []
            for page in pages:
                for alarm in page['MetricAlarms']:
                    alarm_name = alarm.get('AlarmName', '')
                    dimensions = alarm.get('Dimensions', [])
                    
                    # Check if alarm belongs to this instance using dimension-based matching
                    belongs_to_instance = (
                        # 1. InstanceId dimension (most reliable - covers 778/841 alarms)
                        any(dim['Name'] == 'InstanceId' and dim['Value'] == instance_id for dim in dimensions) or

                        # 2. Server dimension for SSM/Composite alarms (covers remaining 63/841 alarms)
                        any(dim['Name'] == 'Server' and dim['Value'].upper() == instance_name.upper() for dim in dimensions)
                    )
                    
                    if belongs_to_instance:
                        instance_alarms.append(alarm)
            return instance_alarms
        except ClientError:
            return []

    def read_file_from_instance(self, instance_id: str, file_path: str, os_type: str = 'linux') -> dict:
        """
        Read a file from an EC2 instance using SSM Run Command.

        Args:
            instance_id: The EC2 instance ID
            file_path: The path to the file on the instance
            os_type: The OS type ('linux' or 'windows')

        Returns:
            dict with keys: 'success' (bool), 'content' (str), 'error' (str)
        """
        try:
            ssm = self.get_cross_account_boto3_client('ssm')
            if not ssm:
                return {'success': False, 'content': '', 'error': 'Failed to get SSM client'}

            # Determine the command based on OS type
            if os_type.lower() == 'windows':
                command = f'Get-Content -Path "{file_path}" -ErrorAction Stop'
                document_name = 'AWS-RunPowerShellScript'
            else:  # linux
                command = f'cat "{file_path}"'
                document_name = 'AWS-RunShellScript'

            # Send command
            response = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName=document_name,
                Parameters={'commands': [command]},
                TimeoutSeconds=30
            )

            command_id = response['Command']['CommandId']

            # Wait for command to complete (with timeout)
            max_attempts = 10
            for attempt in range(max_attempts):
                time.sleep(1)

                try:
                    result = ssm.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id
                    )

                    status = result['Status']

                    if status == 'Success':
                        return {
                            'success': True,
                            'content': result.get('StandardOutputContent', ''),
                            'error': ''
                        }
                    elif status in ['Failed', 'Cancelled', 'TimedOut']:
                        return {
                            'success': False,
                            'content': '',
                            'error': result.get('StandardErrorContent', f'Command {status}')
                        }
                    # If status is 'InProgress' or 'Pending', continue waiting

                except ClientError as e:
                    if 'InvocationDoesNotExist' in str(e):
                        # Command not yet registered, keep waiting
                        continue
                    else:
                        raise

            return {
                'success': False,
                'content': '',
                'error': 'Command timeout - took too long to execute'
            }

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'error': str(e)
            }