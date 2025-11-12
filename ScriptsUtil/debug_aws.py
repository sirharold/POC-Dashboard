import boto3
from botocore.exceptions import ClientError
import json

ROLE_TO_ASSUME_ARN = "arn:aws:iam::011528297340:role/RecolectorDeDashboard"

print("--- Paso 1: Intentando asumir el rol ---")
print(f"ARN del Rol: {ROLE_TO_ASSUME_ARN}")

try:
    sts_client = boto3.client('sts')
    response = sts_client.assume_role(
        RoleArn=ROLE_TO_ASSUME_ARN,
        RoleSessionName='DebugScriptSession'
    )
    credentials = response['Credentials']
    print("¡Éxito! Rol asumido correctamente.")
    
    print("\n--- Paso 2: Creando cliente EC2 con credenciales temporales ---")
    ec2_client = boto3.client(
        'ec2',
        region_name='us-east-1',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
    )
    print("Cliente EC2 creado.")

    print("\n--- Paso 3: Buscando instancias con el tag 'DashboardGroup' ---")
    paginator = ec2_client.get_paginator('describe_instances')
    instance_pages_iterator = paginator.paginate( # Cambiado a iterator para poder re-iterar
        Filters=[{'Name': 'tag-key', 'Values': ['DashboardGroup']}]
    )

    all_instances_data = []
    for page in instance_pages_iterator:
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                all_instances_data.append(instance)

    if all_instances_data:
        print(f"\n¡ÉXITO! Se encontraron {len(all_instances_data)} instancia(s) con el tag 'DashboardGroup':")
        for instance in all_instances_data:
            instance_id = instance['InstanceId']
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            instance_name = tags.get('Name', 'N/A')
            print(f"- ID: {instance_id}, Nombre: {instance_name}, Tags: {tags}")
    else:
        print("\nEl comando se ejecutó correctamente, pero no se encontró ninguna instancia con el tag 'DashboardGroup'.")
        print("ACCIÓN REQUERIDA: Verifica en la Cuenta Cliente que las instancias que quieres monitorear tienen un tag con Key='DashboardGroup' (mayúsculas y minúsculas importan).")

except ClientError as e:
    print(f"\nERROR: {e}")
    if e.response['Error']['Code'] == 'AccessDenied':
        print("\nCausa Probable: Error de 'Access Denied'.")
        print("ACCIÓN REQUERIDA:")
        print("1. Revisa que el rol de la instancia EC2 en la Cuenta Sandbox tenga el permiso 'sts:AssumeRole' sobre el ARN del rol de la Cuenta Cliente.")
        print("2. Revisa que la 'Trust Policy' del rol 'RecolectorDeDashboard' en la Cuenta Cliente confíe en la Cuenta Sandbox.")
    else:
        print("\nOcurrió un error inesperado de cliente de AWS.")

except Exception as e:
    print(f"\nERROR INESPERADO: {e}")