#!/bin/bash
# Script con soluciones alternativas para problemas de red en Fargate
# Ejecuta este script si diagnose_network.sh identifica problemas

set -e

REGION="us-east-1"
VPC_ID="vpc-029a13c34d0d033f0"
CLUSTER_NAME="streamlit-dashboard-cluster"
SERVICE_NAME="streamlit-dashboard-service"
TASK_DEFINITION_NAME="streamlit-dashboard-task"

echo "========================================"
echo "SOLUCIONES PARA PROBLEMAS DE RED"
echo "========================================"
echo ""
echo "Selecciona una opción:"
echo ""
echo "1. Cambiar a subnets alternativas (diferentes AZs)"
echo "2. Cambiar configuración de red (assignPublicIp=DISABLED con NAT)"
echo "3. Reiniciar servicio con nueva tarea"
echo "4. Verificar y limpiar ENIs huérfanas"
echo "5. Ver subnets disponibles en la VPC"
echo "6. Salir"
echo ""
read -p "Opción: " OPTION

case $OPTION in
    1)
        echo ""
        echo "Buscando todas las subnets en la VPC..."
        aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" \
            --query 'Subnets[*].{ID:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock,AvailableIPs:AvailableIpAddressCount,Public:MapPublicIpOnLaunch}' \
            --output table \
            --region $REGION

        echo ""
        echo "Selecciona 2 subnets de DIFERENTES AZs (separadas por coma):"
        echo "Ejemplo: subnet-abc123,subnet-def456"
        read -p "Subnets: " NEW_SUBNETS

        echo ""
        echo "Actualizando servicio con nuevas subnets: $NEW_SUBNETS"

        # Obtener security group actual
        FARGATE_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=$SERVICE_NAME-sg" \
            --query "SecurityGroups[0].GroupId" \
            --output text \
            --region $REGION)

        # Actualizar servicio
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $SERVICE_NAME \
            --network-configuration "awsvpcConfiguration={subnets=[$(echo $NEW_SUBNETS | tr ',' ',')],securityGroups=[$FARGATE_SG_ID],assignPublicIp=ENABLED}" \
            --force-new-deployment \
            --region $REGION

        echo "✅ Servicio actualizado con nuevas subnets"
        echo "Esperando estabilización (esto puede tomar varios minutos)..."
        aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION
        echo "✅ Servicio estable"
        ;;

    2)
        echo ""
        echo "⚠️  WARNING: Esta opción requiere que tus subnets tengan NAT Gateway configurado"
        echo "¿Estás seguro de cambiar assignPublicIp a DISABLED? (yes/no)"
        read -p "Confirmar: " CONFIRM

        if [ "$CONFIRM" == "yes" ]; then
            FARGATE_SG_ID=$(aws ec2 describe-security-groups \
                --filters "Name=group-name,Values=$SERVICE_NAME-sg" \
                --query "SecurityGroups[0].GroupId" \
                --output text \
                --region $REGION)

            # Obtener subnets actuales del servicio
            CURRENT_SUBNETS=$(aws ecs describe-services \
                --cluster $CLUSTER_NAME \
                --services $SERVICE_NAME \
                --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
                --output json \
                --region $REGION | jq -r 'join(",")')

            echo "Actualizando servicio con assignPublicIp=DISABLED..."
            aws ecs update-service \
                --cluster $CLUSTER_NAME \
                --service $SERVICE_NAME \
                --network-configuration "awsvpcConfiguration={subnets=[$CURRENT_SUBNETS],securityGroups=[$FARGATE_SG_ID],assignPublicIp=DISABLED}" \
                --force-new-deployment \
                --region $REGION

            echo "✅ Servicio actualizado"
        else
            echo "Operación cancelada"
        fi
        ;;

    3)
        echo ""
        echo "Deteniendo el servicio actual..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $SERVICE_NAME \
            --desired-count 0 \
            --region $REGION

        echo "Esperando que todas las tareas se detengan..."
        sleep 30

        echo "Reiniciando servicio..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $SERVICE_NAME \
            --desired-count 1 \
            --force-new-deployment \
            --region $REGION

        echo "✅ Servicio reiniciado"
        echo "Esperando estabilización..."
        aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION
        echo "✅ Servicio estable"
        ;;

    4)
        echo ""
        echo "Buscando ENIs (Elastic Network Interfaces) huérfanas..."

        # Buscar ENIs asociadas a las tareas Fargate pero sin tarea activa
        ORPHAN_ENIS=$(aws ec2 describe-network-interfaces \
            --filters "Name=description,Values=*ecs*" "Name=status,Values=available" \
            --query 'NetworkInterfaces[*].{ID:NetworkInterfaceId,Description:Description,Status:Status}' \
            --output json \
            --region $REGION)

        echo "$ORPHAN_ENIS" | jq '.'

        if echo "$ORPHAN_ENIS" | jq -e '. | length > 0' > /dev/null 2>&1; then
            echo ""
            echo "Se encontraron ENIs huérfanas. ¿Deseas eliminarlas? (yes/no)"
            echo "⚠️  Solo elimina ENIs que estés seguro que no están en uso"
            read -p "Confirmar: " CONFIRM_DELETE

            if [ "$CONFIRM_DELETE" == "yes" ]; then
                echo "$ORPHAN_ENIS" | jq -r '.[].ID' | while read eni_id; do
                    echo "Eliminando ENI: $eni_id"
                    aws ec2 delete-network-interface \
                        --network-interface-id $eni_id \
                        --region $REGION 2>&1 || echo "  No se pudo eliminar (puede estar en uso)"
                done
                echo "✅ Proceso completado"
            else
                echo "Operación cancelada"
            fi
        else
            echo "No se encontraron ENIs huérfanas"
        fi
        ;;

    5)
        echo ""
        echo "Subnets disponibles en la VPC: $VPC_ID"
        echo ""
        aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" \
            --query 'Subnets[*].{ID:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock,AvailableIPs:AvailableIpAddressCount,Public:MapPublicIpOnLaunch,RouteTable:Tags[?Key==`Name`]|[0].Value}' \
            --output table \
            --region $REGION

        echo ""
        echo "Recomendaciones:"
        echo "- Usa subnets con AvailableIPs > 10"
        echo "- Selecciona subnets en DIFERENTES AZs para alta disponibilidad"
        echo "- Para assignPublicIp=ENABLED, usa subnets públicas (Public=true)"
        echo "- Para assignPublicIp=DISABLED, usa subnets privadas con NAT Gateway"
        ;;

    6)
        echo "Saliendo..."
        exit 0
        ;;

    *)
        echo "Opción inválida"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "Verifica el estado del servicio:"
echo "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"
echo ""
echo "Ver eventos recientes:"
echo "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].events[0:10]' --output table --region $REGION"
echo "========================================"
