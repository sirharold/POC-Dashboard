"""
Script to explore SAP Availability metrics in CloudWatch.

Namespaces:
- Production: SAP_Monitoring_Availability_Prod
- QA/DEV: SAP_Monitoring_Availability

Metric naming convention:
- {ServerName}_{Path}_{Service}_heartbeat
- Examples: DMZ-SRVWDPRD_DAA_SMDA98_heartbeat, SRVBWPRD_BIP_D00_heartbeat
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import pandas as pd
from services.aws_service import AWSService


def list_metrics_in_namespace(aws_service, namespace):
    """List all metrics in a CloudWatch namespace."""
    print(f"\n{'='*80}")
    print(f"Explorando namespace: {namespace}")
    print(f"{'='*80}\n")

    cloudwatch = aws_service.get_cross_account_boto3_client('cloudwatch')
    if not cloudwatch:
        print("❌ No se pudo obtener cliente de CloudWatch")
        return []

    try:
        paginator = cloudwatch.get_paginator('list_metrics')
        page_iterator = paginator.paginate(Namespace=namespace)

        all_metrics = []
        for page in page_iterator:
            all_metrics.extend(page['Metrics'])

        print(f"Total de métricas encontradas: {len(all_metrics)}")

        # Show first 20 metrics
        print(f"\nPrimeras 20 métricas:")
        for i, metric in enumerate(all_metrics[:20], 1):
            metric_name = metric['MetricName']
            dimensions = metric.get('Dimensions', [])
            dim_str = ', '.join([f"{d['Name']}={d['Value']}" for d in dimensions])
            print(f"{i:3d}. {metric_name}")
            if dim_str:
                print(f"      Dimensions: {dim_str}")

        # Find QA server metrics
        print(f"\n{'='*80}")
        print("Métricas de servidores QA (buscando 'QA' en el nombre):")
        print(f"{'='*80}\n")

        qa_metrics = [m for m in all_metrics if 'QA' in m['MetricName'].upper()]
        print(f"Total de métricas QA: {len(qa_metrics)}")

        for i, metric in enumerate(qa_metrics[:10], 1):
            print(f"{i:3d}. {metric['MetricName']}")

        return all_metrics

    except Exception as e:
        print(f"Error listando métricas: {e}")
        return []


def get_metric_data(aws_service, namespace, metric_name, dimensions, start_time, end_time):
    """Get metric data for specific metric with dimensions."""
    print(f"\n{'='*80}")
    print(f"Obteniendo datos para: {metric_name}")
    dim_str = ', '.join([f"{d['Name']}={d['Value']}" for d in dimensions])
    print(f"Dimensions: {dim_str}")
    print(f"Periodo: {start_time.strftime('%Y-%m-%d')} a {end_time.strftime('%Y-%m-%d')}")
    print(f"{'='*80}\n")

    cloudwatch = aws_service.get_cross_account_boto3_client('cloudwatch')
    if not cloudwatch:
        print("❌ No se pudo obtener cliente de CloudWatch")
        return None

    try:
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=900,  # 15 minutes
            Statistics=['Average', 'Minimum', 'Maximum']
        )

        if not response['Datapoints']:
            print(f"⚠️  No hay datos para {metric_name}")
            return None

        df = pd.DataFrame(response['Datapoints'])
        df = df.sort_values(by='Timestamp').reset_index(drop=True)

        print(f"✅ {len(df)} datapoints obtenidos")
        print(f"\nPrimeros 5 registros:")
        print(df.head())

        print(f"\nÚltimos 5 registros:")
        print(df.tail())

        # Statistics
        print(f"\n📊 Estadísticas:")
        print(f"  - Average: min={df['Average'].min():.2f}, max={df['Average'].max():.2f}, mean={df['Average'].mean():.2f}")
        print(f"  - Minimum: min={df['Minimum'].min():.2f}, max={df['Minimum'].max():.2f}")
        print(f"  - Maximum: min={df['Maximum'].min():.2f}, max={df['Maximum'].max():.2f}")

        return df

    except Exception as e:
        print(f"❌ Error obteniendo datos: {e}")
        return None


def main():
    """Main exploration function."""
    print("\n" + "="*80)
    print("EXPLORACIÓN DE MÉTRICAS DE AVAILABILITY")
    print("="*80)

    # Initialize AWS Service
    print("\nInicializando AWSService...")
    aws_service = AWSService()
    print("✅ AWSService inicializado")

    # Explore both namespaces
    namespaces = [
        'SAP_Monitoring_Availability',          # QA and DEV
        'SAP_Monitoring_Availability_Prod'      # Production
    ]

    all_metrics_by_namespace = {}

    for namespace in namespaces:
        metrics = list_metrics_in_namespace(aws_service, namespace)
        all_metrics_by_namespace[namespace] = metrics

    # Try to get data for a couple of QA servers
    print("\n" + "="*80)
    print("OBTENIENDO DATOS DE EJEMPLO (QA)")
    print("="*80)

    # Date range: last 7 days
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)

    qa_namespace = 'SAP_Monitoring_Availability'
    qa_metrics = all_metrics_by_namespace.get(qa_namespace, [])

    # Find some QA server metrics to test
    qa_heartbeat_metrics = [m for m in qa_metrics if 'heartbeat' in m['MetricName'].lower()]

    print(f"\nMétricas heartbeat encontradas: {len(qa_heartbeat_metrics)}")

    # Test first 5 metrics with their dimensions
    test_count = min(5, len(qa_heartbeat_metrics))
    for i, metric in enumerate(qa_heartbeat_metrics[:test_count], 1):
        metric_name = metric['MetricName']
        dimensions = metric.get('Dimensions', [])

        print(f"\n{'*'*80}")
        print(f"TEST {i}/{test_count}: {metric_name}")
        print(f"{'*'*80}")

        df = get_metric_data(aws_service, qa_namespace, metric_name, dimensions, start_time, end_time)

        if df is not None:
            print(f"\n✅ Métrica {metric_name} tiene datos válidos")
            print(f"   Datapoints: {len(df)}")
            print(f"   Average range: {df['Average'].min():.2f} - {df['Average'].max():.2f}")
        else:
            print(f"\n⚠️  Métrica {metric_name} no tiene datos")

    print("\n" + "="*80)
    print("EXPLORACIÓN COMPLETADA")
    print("="*80)


if __name__ == "__main__":
    main()
