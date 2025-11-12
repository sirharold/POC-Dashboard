#!/usr/bin/env python3
"""
Script de debug para probar la conexión a AWS localmente.
"""

import boto3
from botocore.exceptions import ClientError
import sys

def test_aws_connection():
    """Test AWS connection and role assumption."""

    role_arn = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"

    print("=" * 80)
    print("🔍 AWS Connection Debug Script")
    print("=" * 80)

    # Step 1: Check current identity
    print("\n1️⃣ Verificando identidad actual...")
    try:
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ Identidad actual:")
        print(f"   UserId: {identity['UserId']}")
        print(f"   Account: {identity['Account']}")
        print(f"   Arn: {identity['Arn']}")
    except Exception as e:
        print(f"❌ Error obteniendo identidad: {e}")
        sys.exit(1)

    # Step 2: Try to assume role
    print(f"\n2️⃣ Intentando asumir rol: {role_arn}")
    try:
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='StreamlitDashboardSession'
        )
        print("✅ Rol asumido exitosamente!")
        print(f"   AssumedRoleId: {response['AssumedRoleUser']['AssumedRoleId']}")
        print(f"   Arn: {response['AssumedRoleUser']['Arn']}")

        credentials = response['Credentials']

    except ClientError as e:
        print(f"❌ Error asumiendo rol:")
        print(f"   Error Code: {e.response['Error']['Code']}")
        print(f"   Error Message: {e.response['Error']['Message']}")
        print(f"\n💡 Posibles soluciones:")
        print(f"   1. Verifica que tu usuario/rol tenga permiso sts:AssumeRole")
        print(f"   2. Verifica que el rol {role_arn} exista")
        print(f"   3. Verifica la trust policy del rol RecolectorDeDashboard")
        sys.exit(1)

    # Step 3: Test EC2 access with assumed role
    print("\n3️⃣ Probando acceso a EC2 con el rol asumido...")
    try:
        ec2_client = boto3.client(
            'ec2',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        response = ec2_client.describe_instances(MaxResults=5)
        instance_count = sum(len(r['Instances']) for r in response['Reservations'])
        print(f"✅ Acceso a EC2 exitoso!")
        print(f"   Primeras instancias encontradas: {instance_count}")

        if instance_count > 0:
            first_instance = response['Reservations'][0]['Instances'][0]
            instance_id = first_instance['InstanceId']
            instance_name = next((tag['Value'] for tag in first_instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')
            print(f"   Ejemplo: {instance_id} - {instance_name}")

    except ClientError as e:
        print(f"❌ Error accediendo a EC2:")
        print(f"   Error Code: {e.response['Error']['Code']}")
        print(f"   Error Message: {e.response['Error']['Message']}")
        sys.exit(1)

    # Step 4: Test CloudWatch access
    print("\n4️⃣ Probando acceso a CloudWatch...")
    try:
        cloudwatch_client = boto3.client(
            'cloudwatch',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        response = cloudwatch_client.describe_alarms(MaxResults=5)
        alarm_count = len(response['MetricAlarms'])
        print(f"✅ Acceso a CloudWatch exitoso!")
        print(f"   Primeras alarmas encontradas: {alarm_count}")

        if alarm_count > 0:
            first_alarm = response['MetricAlarms'][0]
            print(f"   Ejemplo: {first_alarm['AlarmName']} - {first_alarm['StateValue']}")

    except ClientError as e:
        print(f"❌ Error accediendo a CloudWatch:")
        print(f"   Error Code: {e.response['Error']['Code']}")
        print(f"   Error Message: {e.response['Error']['Message']}")
        sys.exit(1)

    # Success!
    print("\n" + "=" * 80)
    print("🎉 TODAS LAS PRUEBAS EXITOSAS!")
    print("=" * 80)
    print("\n✅ Tu configuración de AWS está correcta.")
    print("✅ Streamlit debería poder conectarse sin problemas.")
    print("\n💡 Si Streamlit sigue sin funcionar, revisa:")
    print("   1. La consola de Streamlit para errores")
    print("   2. Que el AWS_PROFILE esté exportado en la misma terminal donde ejecutas Streamlit")
    print("   3. Limpia el cache de Streamlit: rm -rf ~/.streamlit/cache")


if __name__ == "__main__":
    test_aws_connection()
