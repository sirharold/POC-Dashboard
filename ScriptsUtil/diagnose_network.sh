#!/bin/bash
# Script para diagnosticar problemas de red en AWS Fargate
# Ayuda a identificar la causa del error: "Timeout waiting for network interface provisioning"

set -e

# Variables (tomadas del script de deploy)
REGION="us-east-1"
VPC_ID="vpc-029a13c34d0d033f0"
SUBNET_IDS="subnet-0ee2c29fb5619f792,subnet-0bdffbaa0174a9736"
CLUSTER_NAME="streamlit-dashboard-cluster"
SERVICE_NAME="streamlit-dashboard-service"

echo "========================================"
echo "DIAGNÓSTICO DE RED - AWS FARGATE"
echo "========================================"
echo ""

# 1. Verificar estado de las subnets
echo "1. VERIFICANDO SUBNETS..."
echo "----------------------------"
IFS=',' read -ra SUBNET_ARRAY <<< "$SUBNET_IDS"
for subnet in "${SUBNET_ARRAY[@]}"; do
    echo ""
    echo "Subnet: $subnet"

    # Obtener información básica
    SUBNET_INFO=$(aws ec2 describe-subnets \
        --subnet-ids $subnet \
        --region $REGION \
        --query 'Subnets[0].{AZ:AvailabilityZone,CIDR:CidrBlock,AvailableIPs:AvailableIpAddressCount,MapPublicIP:MapPublicIpOnLaunch}' \
        --output json 2>&1)

    if [ $? -eq 0 ]; then
        echo "$SUBNET_INFO" | jq '.'

        # Verificar IPs disponibles
        AVAILABLE_IPS=$(echo "$SUBNET_INFO" | jq -r '.AvailableIPs')
        if [ "$AVAILABLE_IPS" -lt 5 ]; then
            echo "⚠️  WARNING: Solo $AVAILABLE_IPS IPs disponibles en esta subnet"
            echo "   Esto podría causar problemas al crear tareas Fargate"
        else
            echo "✅ IPs disponibles: $AVAILABLE_IPS"
        fi

        # Verificar asignación automática de IP pública
        MAP_PUBLIC=$(echo "$SUBNET_INFO" | jq -r '.MapPublicIP')
        if [ "$MAP_PUBLIC" == "false" ]; then
            echo "ℹ️  Esta subnet NO asigna IPs públicas automáticamente"
            echo "   (Configuración actual del deploy: assignPublicIp=ENABLED)"
        fi
    else
        echo "❌ ERROR: No se pudo obtener información de la subnet"
        echo "$SUBNET_INFO"
    fi
done

echo ""
echo "2. VERIFICANDO INTERNET GATEWAY..."
echo "----------------------------"
IGW_ID=$(aws ec2 describe-internet-gateways \
    --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
    --query 'InternetGateways[0].InternetGatewayId' \
    --output text \
    --region $REGION 2>&1)

if [ "$IGW_ID" != "None" ] && [ -n "$IGW_ID" ] && [ "$IGW_ID" != "" ]; then
    echo "✅ Internet Gateway encontrado: $IGW_ID"
else
    echo "❌ ERROR: No se encontró Internet Gateway para la VPC"
    echo "   Las tareas Fargate con assignPublicIp=ENABLED necesitan un IGW"
fi

echo ""
echo "3. VERIFICANDO ROUTE TABLES..."
echo "----------------------------"
for subnet in "${SUBNET_ARRAY[@]}"; do
    echo ""
    echo "Routes para subnet: $subnet"

    # Obtener route table asociada
    ROUTE_TABLE=$(aws ec2 describe-route-tables \
        --filters "Name=association.subnet-id,Values=$subnet" \
        --query 'RouteTables[0].RouteTableId' \
        --output text \
        --region $REGION 2>&1)

    if [ "$ROUTE_TABLE" == "None" ] || [ -z "$ROUTE_TABLE" ]; then
        # Si no hay asociación explícita, buscar la route table principal
        ROUTE_TABLE=$(aws ec2 describe-route-tables \
            --filters "Name=vpc-id,Values=$VPC_ID" "Name=association.main,Values=true" \
            --query 'RouteTables[0].RouteTableId' \
            --output text \
            --region $REGION 2>&1)
        echo "ℹ️  Usando Route Table principal: $ROUTE_TABLE"
    else
        echo "Route Table: $ROUTE_TABLE"
    fi

    # Verificar ruta a internet
    HAS_IGW_ROUTE=$(aws ec2 describe-route-tables \
        --route-table-ids $ROUTE_TABLE \
        --query 'RouteTables[0].Routes[?GatewayId!=`null` && starts_with(GatewayId, `igw-`)].DestinationCidrBlock' \
        --output text \
        --region $REGION 2>&1)

    if [ -n "$HAS_IGW_ROUTE" ]; then
        echo "✅ Ruta a Internet Gateway: $HAS_IGW_ROUTE"
    else
        echo "⚠️  WARNING: No hay ruta a Internet Gateway"
        echo "   Verificando NAT Gateway..."

        HAS_NAT_ROUTE=$(aws ec2 describe-route-tables \
            --route-table-ids $ROUTE_TABLE \
            --query 'RouteTables[0].Routes[?NatGatewayId!=`null`].DestinationCidrBlock' \
            --output text \
            --region $REGION 2>&1)

        if [ -n "$HAS_NAT_ROUTE" ]; then
            echo "✅ Ruta a NAT Gateway: $HAS_NAT_ROUTE"
        else
            echo "❌ ERROR: No hay ruta a Internet (ni IGW ni NAT)"
            echo "   Las tareas Fargate necesitan acceso a Internet para:"
            echo "   - Descargar imágenes de ECR"
            echo "   - Enviar logs a CloudWatch"
        fi
    fi
done

echo ""
echo "4. VERIFICANDO SECURITY GROUPS..."
echo "----------------------------"
FARGATE_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SERVICE_NAME-sg" \
    --query "SecurityGroups[0].GroupId" \
    --output text \
    --region $REGION 2>&1)

if [ "$FARGATE_SG_ID" != "None" ] && [ -n "$FARGATE_SG_ID" ]; then
    echo "Security Group de Fargate: $FARGATE_SG_ID"

    # Verificar reglas de salida
    EGRESS_RULES=$(aws ec2 describe-security-groups \
        --group-ids $FARGATE_SG_ID \
        --query 'SecurityGroups[0].IpPermissionsEgress[?IpProtocol==`-1`]' \
        --output json \
        --region $REGION 2>&1)

    if echo "$EGRESS_RULES" | jq -e '. | length > 0' > /dev/null 2>&1; then
        echo "✅ Reglas de salida permiten todo el tráfico"
    else
        echo "⚠️  WARNING: Las reglas de salida están restringidas"
        echo "   Asegúrate de permitir tráfico HTTPS (443) hacia:"
        echo "   - ECR (para descargar imágenes)"
        echo "   - CloudWatch (para logs)"
    fi
else
    echo "❌ ERROR: No se encontró el Security Group de Fargate"
fi

echo ""
echo "5. VERIFICANDO ESTADO DEL SERVICIO ECS..."
echo "----------------------------"
SERVICE_INFO=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount}' \
    --output json \
    --region $REGION 2>&1)

if [ $? -eq 0 ]; then
    echo "$SERVICE_INFO" | jq '.'
else
    echo "⚠️  No se pudo obtener información del servicio (puede que no exista aún)"
fi

echo ""
echo "6. ÚLTIMOS EVENTOS DEL SERVICIO..."
echo "----------------------------"
aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].events[0:5].{Time:createdAt,Message:message}' \
    --output table \
    --region $REGION 2>&1 || echo "⚠️  No se pudieron obtener eventos del servicio"

echo ""
echo "7. TAREAS FALLIDAS RECIENTES..."
echo "----------------------------"
STOPPED_TASKS=$(aws ecs list-tasks \
    --cluster $CLUSTER_NAME \
    --desired-status STOPPED \
    --query 'taskArns[0:3]' \
    --output json \
    --region $REGION 2>&1)

if echo "$STOPPED_TASKS" | jq -e '. | length > 0' > /dev/null 2>&1; then
    echo "Últimas 3 tareas detenidas:"
    echo "$STOPPED_TASKS" | jq -r '.[]' | while read task_arn; do
        echo ""
        echo "Task: $task_arn"
        aws ecs describe-tasks \
            --cluster $CLUSTER_NAME \
            --tasks $task_arn \
            --query 'tasks[0].{StoppedReason:stoppedReason,StopCode:stopCode}' \
            --output json \
            --region $REGION | jq '.'
    done
else
    echo "No se encontraron tareas detenidas recientes"
fi

echo ""
echo "========================================"
echo "DIAGNÓSTICO COMPLETADO"
echo "========================================"
echo ""
echo "RECOMENDACIONES:"
echo ""
echo "Si ves errores relacionados con IPs:"
echo "  → Considera usar subnets más grandes o con más IPs disponibles"
echo ""
echo "Si ves errores relacionados con rutas:"
echo "  → Verifica que las subnets tengan ruta a Internet (IGW o NAT)"
echo "  → Para subnets públicas: necesitas IGW + assignPublicIp=ENABLED"
echo "  → Para subnets privadas: necesitas NAT Gateway"
echo ""
echo "Si ves timeout de network interface:"
echo "  → Prueba cambiar a subnets diferentes (diferentes AZs)"
echo "  → Verifica que no haya problemas en la región de AWS"
echo "  → Considera usar assignPublicIp=DISABLED con NAT Gateway"
echo ""
