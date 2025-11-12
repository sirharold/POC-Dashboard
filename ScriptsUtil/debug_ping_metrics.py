#!/usr/bin/env python3
"""
Script to debug PingReachable metrics for a specific instance.
"""

import boto3
from datetime import datetime, timedelta
import sys

def debug_ping_metrics(instance_name):
    """Debug ping metrics availability for an instance."""

    role_arn = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"

    print("=" * 80)
    print(f"🔍 Debug Ping Metrics for: {instance_name}")
    print("=" * 80)

    try:
        # Assume role
        sts_client = boto3.client('sts')
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='PingDebugSession'
        )

        credentials = response['Credentials']
        cloudwatch = boto3.client(
            'cloudwatch',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        ec2 = boto3.client(
            'ec2',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        # Step 1: Find instance by name
        print(f"\n1️⃣ Buscando instancia: {instance_name}")
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [instance_name]}
            ]
        )

        if not response['Reservations']:
            print(f"❌ No se encontró instancia con nombre: {instance_name}")
            return

        instance = response['Reservations'][0]['Instances'][0]
        instance_id = instance['InstanceId']
        print(f"✅ Encontrada: {instance_id}")

        # Step 2: List all metrics for this instance
        print(f"\n2️⃣ Buscando métricas disponibles para {instance_name}...")

        # Search in common namespaces
        namespaces = ['EC2/ICMPHealthcheck', 'CWAgent', 'AWS/EC2', 'AWS/ApplicationELB', 'System/Linux']

        all_metrics = []
        for namespace in namespaces:
            print(f"\n   Namespace: {namespace}")

            # Try different dimension combinations
            dimension_sets = [
                [{'Name': 'InstanceId', 'Value': instance_id}],
                [{'Name': 'Name', 'Value': instance_name}],
                [{'Name': 'host', 'Value': instance_name}],
                [{'Name': 'Host', 'Value': instance_name}],
            ]

            for dimensions in dimension_sets:
                try:
                    paginator = cloudwatch.get_paginator('list_metrics')

                    params = {'Namespace': namespace}
                    if dimensions:
                        params['Dimensions'] = dimensions

                    for page in paginator.paginate(**params):
                        for metric in page['Metrics']:
                            metric_key = (metric['MetricName'], tuple(sorted([(d['Name'], d['Value']) for d in metric['Dimensions']])))
                            if metric_key not in [m[0] for m in all_metrics]:
                                all_metrics.append((metric_key, metric))

                                # Check if this is a ping-related metric
                                if 'ping' in metric['MetricName'].lower() or 'reachable' in metric['MetricName'].lower():
                                    print(f"   🎯 PING METRIC FOUND!")
                                    print(f"      Metric: {metric['MetricName']}")
                                    print(f"      Dimensions: {metric['Dimensions']}")
                except Exception as e:
                    pass

        if not all_metrics:
            print(f"   ❌ No se encontraron métricas para este namespace y dimensiones")

        # Step 3: Show all metrics found
        print(f"\n3️⃣ Resumen de métricas encontradas:")
        print("=" * 80)

        if all_metrics:
            # Group by namespace
            by_namespace = {}
            for _, metric in all_metrics:
                ns = metric['Namespace']
                if ns not in by_namespace:
                    by_namespace[ns] = []
                by_namespace[ns].append(metric)

            for ns, metrics in by_namespace.items():
                print(f"\n📊 Namespace: {ns} ({len(metrics)} métricas)")
                for metric in metrics[:10]:  # Show first 10
                    dims = ', '.join([f"{d['Name']}={d['Value']}" for d in metric['Dimensions']])
                    print(f"   • {metric['MetricName']}")
                    print(f"     Dimensions: {dims}")

                if len(metrics) > 10:
                    print(f"   ... y {len(metrics) - 10} más")
        else:
            print("❌ No se encontraron métricas")

        # Step 4: Try to get actual data for PingReachable
        print(f"\n4️⃣ Intentando obtener datos de PingReachable...")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        test_cases = [
            ('EC2/ICMPHealthcheck', 'PingReachable', [{'Name': 'InstanceId', 'Value': instance_id}]),
            ('EC2/ICMPHealthcheck', 'PingReachable', [{'Name': 'Name', 'Value': instance_name}]),
            ('EC2/ICMPHealthcheck', 'PingReachable', [{'Name': 'host', 'Value': instance_name}]),
            ('EC2/ICMPHealthcheck', 'PingReachable', [{'Name': 'Host', 'Value': instance_name}]),
            ('CWAgent', 'PingReachable', [{'Name': 'InstanceId', 'Value': instance_id}]),
            ('CWAgent', 'PingReachable', [{'Name': 'Name', 'Value': instance_name}]),
            ('AWS/EC2', 'StatusCheckFailed', [{'Name': 'InstanceId', 'Value': instance_id}]),
        ]

        for namespace, metric_name, dimensions in test_cases:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1 hour
                    Statistics=['Average']
                )

                if response['Datapoints']:
                    print(f"\n✅ DATOS ENCONTRADOS!")
                    print(f"   Namespace: {namespace}")
                    print(f"   Metric: {metric_name}")
                    print(f"   Dimensions: {dimensions}")
                    print(f"   Datapoints: {len(response['Datapoints'])}")
                    print(f"   Último valor: {response['Datapoints'][-1]}")

            except Exception as e:
                pass

        print("\n" + "=" * 80)
        print("💡 RECOMENDACIONES:")
        print("   1. Verifica el namespace correcto")
        print("   2. Verifica el nombre exacto de la métrica")
        print("   3. Verifica las dimensiones correctas")
        print("   4. Asegúrate que el CloudWatch Agent esté reportando datos")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    instance_name = sys.argv[1] if len(sys.argv) > 1 else "SRVERPQA"
    debug_ping_metrics(instance_name)
