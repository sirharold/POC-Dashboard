#!/usr/bin/env python3
"""
Script to analyze CloudWatch alarm dimensions to determine if all alarms have InstanceId.
This will help decide if we can simplify the alarm filtering logic.
"""

import boto3
from botocore.exceptions import ClientError

def analyze_alarm_dimensions():
    """Analyze all CloudWatch alarms to see which have InstanceId dimension."""

    role_arn = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"

    try:
        # Assume role
        sts_client = boto3.client('sts')
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='AlarmAnalysisSession'
        )

        credentials = response['Credentials']
        cloudwatch = boto3.client(
            'cloudwatch',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        # Get all alarms
        paginator = cloudwatch.get_paginator('describe_alarms')

        alarms_with_instance_id = []
        alarms_without_instance_id = []
        sap_alarms_with_instance_id = []
        sap_alarms_without_instance_id = []

        print("Analyzing all CloudWatch alarms...")
        print("=" * 80)

        for page in paginator.paginate():
            for alarm in page['MetricAlarms']:
                alarm_name = alarm.get('AlarmName', '')
                dimensions = alarm.get('Dimensions', [])

                # Check if alarm has InstanceId dimension
                has_instance_id = any(d['Name'] == 'InstanceId' for d in dimensions)

                # Check if it's a SAP/EPMAPS alarm
                is_sap_alarm = ('SAP' in alarm_name.upper() or 'EPMAPS' in alarm_name.upper())

                if has_instance_id:
                    alarms_with_instance_id.append(alarm_name)
                    if is_sap_alarm:
                        sap_alarms_with_instance_id.append({
                            'name': alarm_name,
                            'dimensions': dimensions
                        })
                else:
                    alarms_without_instance_id.append(alarm_name)
                    if is_sap_alarm:
                        sap_alarms_without_instance_id.append({
                            'name': alarm_name,
                            'dimensions': dimensions
                        })

        # Print summary
        print(f"\n📊 SUMMARY:")
        print(f"Total alarms with InstanceId dimension: {len(alarms_with_instance_id)}")
        print(f"Total alarms WITHOUT InstanceId dimension: {len(alarms_without_instance_id)}")
        print(f"\nSAP/EPMAPS alarms with InstanceId: {len(sap_alarms_with_instance_id)}")
        print(f"SAP/EPMAPS alarms WITHOUT InstanceId: {len(sap_alarms_without_instance_id)}")

        # Show SAP alarms without InstanceId (these are the problematic ones)
        if sap_alarms_without_instance_id:
            print(f"\n⚠️  SAP/EPMAPS ALARMS WITHOUT InstanceId DIMENSION:")
            print("=" * 80)
            for alarm in sap_alarms_without_instance_id[:10]:  # Show first 10
                print(f"\nAlarm: {alarm['name']}")
                print(f"Dimensions: {alarm['dimensions']}")

            if len(sap_alarms_without_instance_id) > 10:
                print(f"\n... and {len(sap_alarms_without_instance_id) - 10} more")

        # Show regular alarms without InstanceId
        if alarms_without_instance_id:
            print(f"\n📋 OTHER ALARMS WITHOUT InstanceId DIMENSION (first 10):")
            print("=" * 80)
            for alarm_name in alarms_without_instance_id[:10]:
                if not ('SAP' in alarm_name.upper() or 'EPMAPS' in alarm_name.upper()):
                    print(f"  - {alarm_name}")

        # Conclusion
        print("\n" + "=" * 80)
        print("🔍 CONCLUSION:")
        if len(sap_alarms_without_instance_id) == 0:
            print("✅ ALL SAP/EPMAPS alarms have InstanceId dimension!")
            print("   You can SAFELY remove the name-based matching logic.")
        else:
            print("⚠️  Some SAP/EPMAPS alarms do NOT have InstanceId dimension.")
            print("   Name-based matching is REQUIRED for these alarms.")
            print("   Recommendation: Fix alarm creation OR keep name-based matching with case-insensitive comparison.")

    except ClientError as e:
        print(f"❌ Error accessing AWS: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    analyze_alarm_dimensions()
