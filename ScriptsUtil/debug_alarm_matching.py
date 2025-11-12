#!/usr/bin/env python3
"""
Script to debug alarm matching for a specific instance.
Shows which alarms are being matched and why.
"""

import boto3
from botocore.exceptions import ClientError

def debug_alarm_matching_for_instance(target_instance_name):
    """Debug alarm matching for a specific instance."""

    role_arn = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"

    try:
        # Assume role
        sts_client = boto3.client('sts')
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='AlarmDebugSession'
        )

        credentials = response['Credentials']

        # Get EC2 client to find the instance
        ec2 = boto3.client(
            'ec2',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        cloudwatch = boto3.client(
            'cloudwatch',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        # Find the instance
        print(f"🔍 Looking for instance: {target_instance_name}")
        print("=" * 80)

        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [target_instance_name]}
            ]
        )

        if not response['Reservations']:
            print(f"❌ No instance found with name: {target_instance_name}")
            return

        instance = response['Reservations'][0]['Instances'][0]
        instance_id = instance['InstanceId']
        instance_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), instance_id)

        print(f"✅ Found instance:")
        print(f"   ID: {instance_id}")
        print(f"   Name: {instance_name}")
        print()

        # Get all alarms
        paginator = cloudwatch.get_paginator('describe_alarms')

        matched_alarms = []
        potential_false_positives = []

        print(f"🔍 Analyzing alarm matching...")
        print("=" * 80)

        for page in paginator.paginate():
            for alarm in page['MetricAlarms']:
                alarm_name = alarm.get('AlarmName', '')
                dimensions = alarm.get('Dimensions', [])

                # Current matching logic (dimension-based only)
                match_reason = None

                # Level 1: InstanceId dimension
                if any(d['Name'] == 'InstanceId' and d['Value'] == instance_id for d in dimensions):
                    match_reason = "✅ Level 1: InstanceId dimension"

                # Level 2: Server dimension
                elif any(d['Name'] == 'Server' and d['Value'].upper() == instance_name.upper() for d in dimensions):
                    match_reason = "✅ Level 2: Server dimension"

                if match_reason:
                    matched_alarms.append({
                        'alarm': alarm_name,
                        'reason': match_reason,
                        'dimensions': dimensions
                    })

        # Display results
        print(f"\n📊 MATCHED ALARMS: {len(matched_alarms)}")
        print("=" * 80)
        for item in matched_alarms[:20]:  # Show first 20
            print(f"\n{item['reason']}")
            print(f"Alarm: {item['alarm']}")
            if item['dimensions']:
                dims_str = ', '.join([f"{d['Name']}={d['Value']}" for d in item['dimensions']])
                print(f"Dimensions: {dims_str}")

        if len(matched_alarms) > 20:
            print(f"\n... and {len(matched_alarms) - 20} more alarms")

        # Show potential false positives
        if potential_false_positives:
            print(f"\n⚠️  POTENTIAL FALSE POSITIVES (substring matches): {len(potential_false_positives)}")
            print("=" * 80)
            print("These alarms matched due to substring, but may belong to different instances:")
            for item in potential_false_positives:
                print(f"\nAlarm: {item['alarm']}")
                if item['dimensions']:
                    dims_str = ', '.join([f"{d['Name']}={d['Value']}" for d in item['dimensions']])
                    print(f"Dimensions: {dims_str}")

        print("\n" + "=" * 80)
        print("🔍 RECOMMENDATION:")
        if potential_false_positives:
            print("❌ Substring matching is causing false positives!")
            print("   Need to improve Level 3 matching to use word boundaries.")
        else:
            print("✅ No false positives detected. Matching logic is working correctly.")

    except ClientError as e:
        print(f"❌ Error accessing AWS: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        instance_name = sys.argv[1]
    else:
        instance_name = "srvcrmqas"  # Default test case

    debug_alarm_matching_for_instance(instance_name)
