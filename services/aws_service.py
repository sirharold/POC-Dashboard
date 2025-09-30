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
                    for alarm in all_alarms:
                        dimensions = alarm.get('Dimensions', [])
                        if any(d['Name'] == 'InstanceId' and d['Value'] == instance_id for d in dimensions):
                            alarms_list_for_instance.append(alarm) # Add the full object
                            alarm_state = alarm.get('StateValue', 'UNKNOWN')
                            alarm_name = alarm.get('AlarmName', '')
                            
                            # Log each alarm for debugging
                            with open("/tmp/streamlit_aws_debug.log", "a") as f:
                                f.write(f"[{time.ctime()}] Alarm: {alarm_name}, State: {alarm_state}, Instance: {instance_id}\n")
                            
                            # Check if this is a preventive alarm
                            if alarm_state == 'ALARM' and ('ALERTA' in alarm_name.upper() or 'PROACTIVA' in alarm_name.upper() or 'PREVENTIVA' in alarm_name.upper()):
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
                        'AlarmObjects': alarms_list_for_instance
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

    def get_log_groups(self, instance_id: str) -> list:
        """Find CloudWatch log groups potentially related to an instance ID."""
        try:
            logs_client = self.get_cross_account_boto3_client('logs')
            if not logs_client: return []

            # Search for log groups with the instance ID in their name
            response = logs_client.describe_log_groups(
                logGroupNamePrefix=f'/aws/ec2/{instance_id}' # A common convention
            )
            
            groups = [lg['logGroupName'] for lg in response.get('logGroups', [])]
            
            # Also search for instance ID directly
            response_alt = logs_client.describe_log_groups(logGroupNamePrefix=f'{instance_id}')
            groups.extend([lg['logGroupName'] for lg in response_alt.get('logGroups', [])])

            return sorted(list(set(groups))) # Return unique, sorted list
        except Exception:
            return []

    def get_log_events(self, log_group_name: str, limit: int = 100) -> list:
        """Get the most recent log events from a CloudWatch log group."""
        try:
            logs_client = self.get_cross_account_boto3_client('logs')
            if not logs_client: return []

            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                limit=limit,
                interleaved=True # Returns events from all streams, sorted by time
            )
            return response.get('events', [])
        except Exception:
            return []

    def get_alarms_for_instance(self, instance_id: str):
        """Get CloudWatch alarms for an instance. Same as original function."""
        try:
            cloudwatch = self.get_cross_account_boto3_client('cloudwatch')
            if not cloudwatch: 
                return []
            paginator = cloudwatch.get_paginator('describe_alarms')
            pages = paginator.paginate()
            instance_alarms = []
            for page in pages:
                for alarm in page['MetricAlarms']:
                    if any(dim['Name'] == 'InstanceId' and dim['Value'] == instance_id for dim in alarm['Dimensions']):
                        instance_alarms.append(alarm)
            return instance_alarms
        except ClientError:
            return []