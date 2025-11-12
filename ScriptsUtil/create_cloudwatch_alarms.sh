#!/bin/bash

# Script para crear alarmas de CloudWatch en instancias EC2
# Autor: Sistema automatizado
# Fecha: $(date)

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables globales
DRY_RUN=false
SNS_TOPIC_ARN=""
ALARM_ACTIONS_ENABLED="true"

# Lista de instancias EC2 y sus nombres
INSTANCE_IDS=("i-0e2618a0aed6a3dcd" "i-0a838c06fbd8c3b8e" "i-018a476f209209fa8")
INSTANCE_NAMES=("SAPLOG2_POC-win" "SAPLOG2_POC-linux" "SAPLOG2_POC-win2")

# Configuración de volúmenes por instancia - usando índices numéricos
INSTANCE_VOLUMES_0="/dev/sda1,C:;/dev/xvdb,D:"      # i-0e2618a0aed6a3dcd
INSTANCE_VOLUMES_1="/dev/xvda,/;/dev/xvdb,/data"   # i-0a838c06fbd8c3b8e
INSTANCE_VOLUMES_2="/dev/sda1,C:;/dev/xvdb,D:"     # i-018a476f209209fa8

# Función para mostrar uso
usage() {
    echo "Uso: $0 [--dry-run] [--sns-topic-arn ARN]"
    echo ""
    echo "Opciones:"
    echo "  --dry-run         Simula la creación de alarmas sin crearlas realmente"
    echo "  --sns-topic-arn   ARN del SNS topic para notificaciones (opcional)"
    echo ""
    exit 1
}

# Procesar argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --sns-topic-arn)
            SNS_TOPIC_ARN="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Opción desconocida: $1"
            usage
            ;;
    esac
done

# Función para crear comando de alarma
create_alarm_command() {
    local alarm_name="$1"
    local description="$2"
    local metric_name="$3"
    local namespace="$4"
    local statistic="$5"
    local period="$6"
    local threshold="$7"
    local comparison="$8"
    local dimensions="$9"
    
    local cmd="aws cloudwatch put-metric-alarm"
    cmd="$cmd --alarm-name \"$alarm_name\""
    cmd="$cmd --alarm-description \"$description\""
    cmd="$cmd --metric-name $metric_name"
    cmd="$cmd --namespace $namespace"
    cmd="$cmd --statistic $statistic"
    cmd="$cmd --period $period"
    cmd="$cmd --evaluation-periods 2"
    cmd="$cmd --threshold $threshold"
    cmd="$cmd --comparison-operator $comparison"
    cmd="$cmd --dimensions $dimensions"
    # No usar --alarm-actions-enabled ya que no es un parámetro válido
    
    if [[ -n "$SNS_TOPIC_ARN" ]]; then
        cmd="$cmd --alarm-actions \"$SNS_TOPIC_ARN\""
    fi
    
    echo "$cmd"
}

# Función para ejecutar o simular comando
execute_command() {
    local cmd="$1"
    local alarm_name="$2"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Alarma: ${BLUE}$alarm_name${NC}"
        echo -e "${YELLOW}[DRY-RUN]${NC} Comando: $cmd"
        echo ""
    else
        echo -e "${GREEN}[EJECUTANDO]${NC} Creando alarma: ${BLUE}$alarm_name${NC}"
        eval "$cmd"
        if [[ $? -eq 0 ]]; then
            echo -e "${GREEN}[OK]${NC} Alarma creada exitosamente"
        else
            echo -e "${RED}[ERROR]${NC} Error al crear la alarma"
        fi
        echo ""
    fi
}

# Función para crear alarmas de CPU
create_cpu_alarms() {
    local instance_id="$1"
    local instance_name="$2"
    
    echo -e "${BLUE}=== Creando alarmas de CPU para $instance_name ($instance_id) ===${NC}"
    
    # Obtener número de CPUs
    local cpu_count=$(aws ec2 describe-instances --instance-ids $instance_id --query 'Reservations[0].Instances[0].CpuOptions.CoreCount' --output text 2>/dev/null)
    if [[ -z "$cpu_count" || "$cpu_count" == "None" ]]; then
        cpu_count=1
    fi
    
    echo -e "Número de CPUs detectadas: ${GREEN}$cpu_count${NC}"
    
    # Alarma CPU 80%
    local alarm_name="${instance_name}-CPU-80-Percent"
    local dimensions="Name=InstanceId,Value=$instance_id"
    local cmd=$(create_alarm_command \
        "$alarm_name" \
        "CPU utilization exceeds 80% on $instance_name" \
        "CPUUtilization" \
        "AWS/EC2" \
        "Average" \
        "300" \
        "80.0" \
        "GreaterThanThreshold" \
        "$dimensions")
    
    execute_command "$cmd" "$alarm_name"
    
    # Alarma CPU 90%
    alarm_name="${instance_name}-CPU-90-Percent"
    cmd=$(create_alarm_command \
        "$alarm_name" \
        "CPU utilization exceeds 90% on $instance_name" \
        "CPUUtilization" \
        "AWS/EC2" \
        "Average" \
        "300" \
        "90.0" \
        "GreaterThanThreshold" \
        "$dimensions")
    
    execute_command "$cmd" "$alarm_name"
    
    # Si hay múltiples CPUs, crear alarmas por CPU
    if [[ $cpu_count -gt 1 ]]; then
        for ((i=0; i<$cpu_count; i++)); do
            # Nota: CloudWatch no proporciona métricas por CPU individual por defecto
            # Se necesitaría CloudWatch Agent para esto
            echo -e "${YELLOW}[INFO]${NC} Para monitoreo por CPU individual, se requiere CloudWatch Agent"
        done
    fi
}

# Función para crear alarmas de disco
create_disk_alarms() {
    local instance_id="$1"
    local instance_name="$2"
    local instance_index="$3"
    
    echo -e "${BLUE}=== Creando alarmas de disco para $instance_name ($instance_id) ===${NC}"
    
    # Para alarmas de disco, necesitamos CloudWatch Agent
    echo -e "${YELLOW}[INFO]${NC} Las alarmas de disco requieren CloudWatch Agent instalado y configurado"
    
    # Obtener volúmenes configurados para esta instancia usando el índice
    local volumes_var="INSTANCE_VOLUMES_${instance_index}"
    local volumes_config="${!volumes_var}"
    local volume_count=0
    
    if [[ -n "$volumes_config" ]]; then
        # Separar volúmenes por punto y coma
        IFS=';' read -ra VOLUMES <<< "$volumes_config"
        
        for volume_info in "${VOLUMES[@]}"; do
            # Separar device y mount point
            IFS=',' read -r device mount_point <<< "$volume_info"
            
            # Determinar el tipo de sistema de archivos basado en el SO
            local fstype="ext4"
            if [[ "$instance_name" == *"win"* ]]; then
                fstype="NTFS"
            fi
            
            local alarm_name="${instance_name}-Disk-Usage-80-Percent-${mount_point//[^a-zA-Z0-9]/-}"
            local dimensions="Name=InstanceId,Value=$instance_id Name=device,Value=$device Name=fstype,Value=$fstype Name=path,Value=$mount_point"
            
            local cmd=$(create_alarm_command \
                "$alarm_name" \
                "Disk usage exceeds 80% on $instance_name ($mount_point)" \
                "disk_used_percent" \
                "CWAgent" \
                "Average" \
                "300" \
                "80.0" \
                "GreaterThanThreshold" \
                "$dimensions")
            
            execute_command "$cmd" "$alarm_name"
            ((volume_count++))
        done
        
        echo -e "${GREEN}[INFO]${NC} Se configuraron $volume_count alarmas de disco para $instance_name"
    else
        echo -e "${YELLOW}[ADVERTENCIA]${NC} No se encontraron volúmenes configurados para $instance_id"
    fi
    
    return $volume_count
}

# Función para crear alarmas de RAM
create_memory_alarms() {
    local instance_id="$1"
    local instance_name="$2"
    
    echo -e "${BLUE}=== Creando alarmas de memoria para $instance_name ($instance_id) ===${NC}"
    
    # Para alarmas de memoria, necesitamos CloudWatch Agent
    echo -e "${YELLOW}[INFO]${NC} Las alarmas de memoria requieren CloudWatch Agent instalado y configurado"
    
    # Alarma de memoria 80%
    local alarm_name="${instance_name}-Memory-80-Percent"
    local dimensions="Name=InstanceId,Value=$instance_id"
    
    local cmd=$(create_alarm_command \
        "$alarm_name" \
        "Memory usage exceeds 80% on $instance_name" \
        "mem_used_percent" \
        "CWAgent" \
        "Average" \
        "300" \
        "80.0" \
        "GreaterThanThreshold" \
        "$dimensions")
    
    execute_command "$cmd" "$alarm_name"
}

# Función principal
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Script de creación de alarmas CloudWatch${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}MODO DRY-RUN ACTIVADO - No se crearán alarmas reales${NC}"
        echo ""
    fi
    
    # Resumen de configuración
    echo -e "${BLUE}Configuración:${NC}"
    echo -e "  Modo: $(if [[ "$DRY_RUN" == "true" ]]; then echo "DRY-RUN"; else echo "EJECUCIÓN"; fi)"
    echo -e "  SNS Topic: $(if [[ -n "$SNS_TOPIC_ARN" ]]; then echo "$SNS_TOPIC_ARN"; else echo "No configurado"; fi)"
    echo -e "  Total de instancias: ${#INSTANCE_IDS[@]}"
    echo ""
    
    # Contador de alarmas
    local total_alarms=0
    
    # Procesar cada instancia
    for i in "${!INSTANCE_IDS[@]}"; do
        local instance_id="${INSTANCE_IDS[$i]}"
        local instance_name="${INSTANCE_NAMES[$i]}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Procesando: $instance_name ($instance_id)${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        
        create_cpu_alarms "$instance_id" "$instance_name"
        total_alarms=$((total_alarms + 2))  # 2 alarmas de CPU
        
        local disk_alarms_created=0
        create_disk_alarms "$instance_id" "$instance_name" "$i"
        disk_alarms_created=$?
        total_alarms=$((total_alarms + disk_alarms_created))
        
        create_memory_alarms "$instance_id" "$instance_name"
        total_alarms=$((total_alarms + 1))  # 1 alarma de memoria
        
        echo ""
    done
    
    # Resumen final
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}RESUMEN${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "Total de alarmas a crear: ${BLUE}$total_alarms${NC}"
    echo -e "  - Alarmas de CPU: $((${#INSTANCE_IDS[@]} * 2)) (2 por instancia)"
    echo -e "  - Alarmas de disco: 6 (2 por instancia - todos tienen 2 volúmenes)"
    echo -e "  - Alarmas de memoria: ${#INSTANCE_IDS[@]} (1 por instancia)"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}Para ejecutar realmente los comandos, ejecute sin --dry-run${NC}"
    else
        echo -e "${GREEN}Proceso completado${NC}"
    fi
}

# Ejecutar función principal
main