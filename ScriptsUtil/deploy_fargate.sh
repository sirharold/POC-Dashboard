#!/bin/bash
set -e

# Función para logging con timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Iniciando el script de despliegue de Streamlit en AWS Fargate..."

# --- Variables de Configuración ---
AWS_ACCOUNT_ID="687634808667"
REGION="us-east-1"
VPC_ID="vpc-029a13c34d0d033f0"
SUBNET_IDS="subnet-09d22124c9930cfc1,subnet-0187f8812f648d6bf"
FARGATE_CPU="2048" # 2 vCPU
FARGATE_MEMORY="4096" # 4 GB
ECR_IMAGE_URI="687634808667.dkr.ecr.us-east-1.amazonaws.com/dashboard-epmaps-poc:latest"

CLUSTER_NAME="streamlit-dashboard-cluster"
ALB_NAME="streamlit-alb"
TG_NAME="streamlit-tg"
TASK_DEFINITION_NAME="streamlit-dashboard-task"
SERVICE_NAME="streamlit-dashboard-service"

# --- 1. Crear Roles de IAM ---
log "1. Creando/Verificando Roles de IAM..."

# ecsTaskExecutionRole
if ! aws iam get-role --role-name ecsTaskExecutionRole &>/dev/null; then
    echo "  Creando ecsTaskExecutionRole..."
    aws iam create-role \
        --role-name ecsTaskExecutionRole \
        --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
        --region $REGION > /dev/null
    aws iam attach-role-policy \
        --role-name ecsTaskExecutionRole \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
        --region $REGION > /dev/null
    echo "  ecsTaskExecutionRole creado."
else
    echo "  ecsTaskExecutionRole ya existe."
fi
ECS_TASK_EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text --region $REGION)
echo "  ARN de ecsTaskExecutionRole: $ECS_TASK_EXECUTION_ROLE_ARN"

# streamlit-task-role (para la aplicación)
if ! aws iam get-role --role-name streamlit-task-role &>/dev/null; then
    echo "  Creando streamlit-task-role..."
    aws iam create-role \
        --role-name streamlit-task-role \
        --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
        --region $REGION > /dev/null
    # Adjunta políticas necesarias para tu aplicación (ej. S3, CloudWatch)
    aws iam attach-role-policy \
        --role-name streamlit-task-role \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
        --region $REGION > /dev/null
    aws iam attach-role-policy \
        --role-name streamlit-task-role \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess \
        --region $REGION > /dev/null
    echo "  streamlit-task-role creado."
else
    echo "  streamlit-task-role ya existe."
fi
STREAMLIT_TASK_ROLE_ARN=$(aws iam get-role --role-name streamlit-task-role --query 'Role.Arn' --output text --region $REGION)
echo "  ARN de streamlit-task-role: $STREAMLIT_TASK_ROLE_ARN"

# --- 2. Configurar Grupos de Seguridad ---
log "2. Creando/Verificando Grupos de Seguridad..."

# SG para ALB
ALB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$ALB_NAME-sg" --query "SecurityGroups[0].GroupId" --output text --region $REGION 2>/dev/null)
if [ "$ALB_SG_ID" == "None" ] || [ -z "$ALB_SG_ID" ]; then
    echo "  Creando Security Group para ALB ($ALB_NAME-sg)..."
    ALB_SG_ID=$(aws ec2 create-security-group \
        --group-name "$ALB_NAME-sg" \
        --description "Security group for Streamlit ALB" \
        --vpc-id $VPC_ID \
        --query 'GroupId' --output text \
        --region $REGION)
    echo "  ID de SG del ALB: $ALB_SG_ID"
    echo "  Añadiendo reglas de entrada para HTTP (80) y HTTPS (443) al SG del ALB..."
    aws ec2 authorize-security-group-ingress \
        --group-id $ALB_SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    aws ec2 authorize-security-group-ingress \
        --group-id $ALB_SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    echo "  Reglas añadidas al SG del ALB."
else
    echo "  Security Group para ALB ($ALB_NAME-sg) ya existe. ID: $ALB_SG_ID"
fi

# SG para Tareas Fargate
FARGATE_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SERVICE_NAME-sg" --query "SecurityGroups[0].GroupId" --output text --region $REGION 2>/dev/null)
if [ "$FARGATE_SG_ID" == "None" ] || [ -z "$FARGATE_SG_ID" ]; then
    echo "  Creando Security Group para Tareas Fargate ($SERVICE_NAME-sg)..."
    FARGATE_SG_ID=$(aws ec2 create-security-group \
        --group-name "$SERVICE_NAME-sg" \
        --description "Security group for Streamlit Fargate tasks" \
        --vpc-id $VPC_ID \
        --query 'GroupId' --output text \
        --region $REGION)
    echo "  ID de SG de Fargate: $FARGATE_SG_ID"
    echo "  Añadiendo regla de entrada para el puerto 8501 desde el SG del ALB al SG de Fargate..."
    aws ec2 authorize-security-group-ingress \
        --group-id $FARGATE_SG_ID \
        --protocol tcp \
        --port 8501 \
        --source-group $ALB_SG_ID \
        --region $REGION
    echo "  Regla añadida al SG de Fargate."
else
    echo "  Security Group para Tareas Fargate ($SERVICE_NAME-sg) ya existe. ID: $FARGATE_SG_ID"
fi

# --- 3. Crear Balanceador de Carga (ALB) y Grupo Objetivo ---
log "3. Creando/Verificando ALB y Target Group..."

# ALB
ALB_ARN=$(aws elbv2 describe-load-balancers --names $ALB_NAME --query "LoadBalancers[0].LoadBalancerArn" --output text --region $REGION 2>/dev/null || true)
if [ "$ALB_ARN" == "None" ] || [ -z "$ALB_ARN" ]; then
    echo "  Creando ALB ($ALB_NAME)..."
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name $ALB_NAME \
        --subnets $(echo $SUBNET_IDS | tr ',' ' ') \
        --security-groups $ALB_SG_ID \
        --scheme internet-facing \
        --type application \
        --query 'LoadBalancers[0].LoadBalancerArn' --output text \
        --region $REGION)
    echo "  ARN del ALB: $ALB_ARN"
    echo "  Esperando que el ALB esté activo (máximo 2 minutos)..."
    timeout 120 aws elbv2 wait load-balancer-available --load-balancer-arns $ALB_ARN --region $REGION || {
        echo "  WARNING: Timeout esperando que el ALB esté activo. Continuando..."
        ALB_STATE=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].State.Code' --output text --region $REGION)
        echo "  Estado actual del ALB: $ALB_STATE"
    }
    echo "  Procediendo con el ALB."
else
    echo "  ALB ($ALB_NAME) ya existe. ARN: $ALB_ARN"
fi

# Target Group
#TG_ARN=$(aws elbv2 describe-target-groups --names $TG_NAME --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION 2>/dev/null)
TG_ARN=$(aws elbv2 describe-target-groups --names $TG_NAME --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION 2>/dev/null || echo "")
if [ "$TG_ARN" == "None" ] || [ -z "$TG_ARN" ]; then
    echo "  Creando Target Grouxp ($TG_NAME)..."
    TG_ARN=$(aws elbv2 create-target-group \
        --name $TG_NAME \
        --protocol HTTP \
        --port 8501 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-protocol HTTP \
        --health-check-path / \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 2 \
        --query 'TargetGroups[0].TargetGroupArn' --output text \
        --region $REGION)
    echo "  ARN del Target Group: $TG_ARN"
else
    echo "  Target Group ($TG_NAME) ya existe. ARN: $TG_ARN"
    # Verificar si está asociado a otro ALB
    ASSOCIATED_ALBS=$(aws elbv2 describe-target-groups --target-group-arns $TG_ARN --query 'TargetGroups[0].LoadBalancerArns' --output text --region $REGION 2>/dev/null)
    if [ -n "$ASSOCIATED_ALBS" ] && [ "$ASSOCIATED_ALBS" != "None" ]; then
        echo "  WARNING: Target Group ya está asociado a otro(s) ALB(s): $ASSOCIATED_ALBS"
        echo "  Creando nuevo Target Group con nombre único..."
        TIMESTAMP=$(date +%s)
        NEW_TG_NAME="${TG_NAME}-${TIMESTAMP}"
        TG_ARN=$(aws elbv2 create-target-group \
            --name $NEW_TG_NAME \
            --protocol HTTP \
            --port 8501 \
            --vpc-id $VPC_ID \
            --target-type ip \
            --health-check-protocol HTTP \
            --health-check-path / \
            --health-check-interval-seconds 30 \
            --health-check-timeout-seconds 5 \
            --healthy-threshold-count 2 \
            --unhealthy-threshold-count 2 \
            --query 'TargetGroups[0].TargetGroupArn' --output text \
            --region $REGION)
        echo "  ARN del nuevo Target Group: $TG_ARN"
    fi
fi

log "  Verificando/Creando Listener..."
# Listener
log "  Obteniendo información del Listener..."
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[?Port==`80`].ListenerArn' --output text --region $REGION 2>/dev/null)
log "  Listener ARN obtenido: $LISTENER_ARN"
if [ "$LISTENER_ARN" == "None" ] || [ -z "$LISTENER_ARN" ]; then
    log "  Creando Listener para el ALB (puerto 80)..."
    aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=$TG_ARN \
        --region $REGION > /dev/null
    log "  Listener creado."
else
    log "  Listener para el puerto 80 ya existe. ARN: $LISTENER_ARN"
    # Verificar si el listener apunta al target group correcto
    CURRENT_TG=$(aws elbv2 describe-listeners --listener-arns $LISTENER_ARN --query 'Listeners[0].DefaultActions[0].TargetGroupArn' --output text --region $REGION 2>/dev/null)
    log "  Target Group actual del listener: $CURRENT_TG"
    if [ "$CURRENT_TG" != "$TG_ARN" ]; then
        log "  Actualizando listener para usar el nuevo target group..."
        aws elbv2 modify-listener \
            --listener-arn $LISTENER_ARN \
            --default-actions Type=forward,TargetGroupArn=$TG_ARN \
            --region $REGION > /dev/null
        log "  Listener actualizado."
    else
        log "  Listener ya apunta al target group correcto."
    fi
fi

# --- 4. Crear Cluster de ECS ---
log "4. Creando/Verificando Cluster de ECS ($CLUSTER_NAME)..."
log "  Verificando si el cluster existe..."
CLUSTER_EXISTS=$(aws ecs describe-clusters --cluster-name $CLUSTER_NAME --query "clusters[0].status" --output text --region $REGION 2>/dev/null || echo "NOT_FOUND")
log "  Estado del cluster: $CLUSTER_EXISTS"
if [ "$CLUSTER_EXISTS" != "ACTIVE" ]; then
    log "  Creando cluster de ECS..."
    aws ecs create-cluster \
        --cluster-name $CLUSTER_NAME \
        --region $REGION > /dev/null
    log "  Cluster de ECS creado."
else
    log "  Cluster de ECS ya existe y está activo."
fi

# --- 5. Crear CloudWatch Log Group ---
log "5. Creando/Verificando CloudWatch Log Group..."
if ! aws logs describe-log-groups --log-group-name-prefix "/ecs/$TASK_DEFINITION_NAME" --query "logGroups[?logGroupName=='/ecs/$TASK_DEFINITION_NAME']" --output text --region $REGION | grep -q "$TASK_DEFINITION_NAME"; then
    echo "  Creando CloudWatch Log Group..."
    aws logs create-log-group \
        --log-group-name "/ecs/$TASK_DEFINITION_NAME" \
        --region $REGION
    echo "  CloudWatch Log Group creado."
else
    echo "  CloudWatch Log Group ya existe."
fi

# --- 6. Registrar Definición de Tarea ---
log "6. Registrando Definición de Tarea ($TASK_DEFINITION_NAME)..."

TASK_DEFINITION_JSON=$(cat <<EOF
{
    "family": "$TASK_DEFINITION_NAME",
    "networkMode": "awsvpc",
    "cpu": "$FARGATE_CPU",
    "memory": "$FARGATE_MEMORY",
    "executionRoleArn": "$ECS_TASK_EXECUTION_ROLE_ARN",
    "taskRoleArn": "$STREAMLIT_TASK_ROLE_ARN",
    "requiresCompatibilities": [
        "FARGATE"
    ],
    "containerDefinitions": [
        {
            "name": "streamlit-app",
            "image": "$ECR_IMAGE_URI",
            "portMappings": [
                {
                    "containerPort": 8501,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "environment": [
                {
                    "name": "STREAMLIT_SERVER_PORT",
                    "value": "8501"
                },
                {
                    "name": "STREAMLIT_SERVER_ADDRESS",
                    "value": "0.0.0.0"
                },
                {
                    "name": "STREAMLIT_SERVER_ENABLE_CORS",
                    "value": "false"
                },
                {
                    "name": "STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION",
                    "value": "false"
                },
                {
                    "name": "STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION",
                    "value": "false"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/$TASK_DEFINITION_NAME",
                    "awslogs-region": "$REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF
)

aws ecs register-task-definition \
    --cli-input-json "$TASK_DEFINITION_JSON" \
    --region $REGION > /dev/null
echo "  Definición de Tarea registrada."

# --- 7. Crear/Actualizar Servicio de ECS ---
log "7. Creando/Actualizando Servicio de ECS ($SERVICE_NAME)..."

SERVICE_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query "services[0].status" --output text --region $REGION 2>/dev/null)

if [ "$SERVICE_STATUS" == "ACTIVE" ]; then
    echo "  Servicio de ECS ($SERVICE_NAME) ya existe. Actualizando..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_DEFINITION_NAME \
        --force-new-deployment \
        --region $REGION > /dev/null
    echo "  Servicio de ECS actualizado."
else
    echo "  Creando Servicio de ECS ($SERVICE_NAME)..."
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $TASK_DEFINITION_NAME \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$(echo $SUBNET_IDS | tr ',' ',')],securityGroups=[$FARGATE_SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers '[{"targetGroupArn":"'"$TG_ARN"'","containerName":"streamlit-app","containerPort":8501}]' \
        --region $REGION > /dev/null
    echo "  Servicio de ECS creado."
fi

# --- 8. Verificación de despliegue ---
log "8. Verificando estado del despliegue..."
echo "  Esperando que las tareas se inicien (máximo 5 minutos)..."
timeout 300 aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION || {
    echo "  WARNING: El servicio tardó más de 5 minutos en estabilizarse."
    echo "  Verificando estado actual..."
    aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query "services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount,Events:events[0:3]}" --region $REGION
}

echo ""
echo "=== DESPLIEGUE COMPLETADO ==="
ALB_DNS=$(aws elbv2 describe-load-balancers --names $ALB_NAME --query 'LoadBalancers[0].DNSName' --output text --region $REGION)
echo "URL de la aplicación: http://$ALB_DNS"
echo "Logs en CloudWatch: /ecs/$TASK_DEFINITION_NAME"
echo ""
echo "Para verificar el estado: aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"