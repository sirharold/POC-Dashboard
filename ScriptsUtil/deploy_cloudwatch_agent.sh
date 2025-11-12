#!/bin/bash

# Script maestro para desplegar CloudWatch Agent en todas las instancias
# Autor: Sistema automatizado
# Fecha: $(date)

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuración de instancias (usando arrays indexados)
INSTANCE_IDS=("i-0e2618a0aed6a3dcd" "i-0a838c06fbd8c3b8e" "i-018a476f209209fa8")
INSTANCE_NAMES=("SAPLOG2_POC-win" "SAPLOG2_POC-linux" "SAPLOG2_POC-win2")
INSTANCE_TYPES=("windows" "linux" "windows")

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY_PATH=""
DRY_RUN=false
SELECTED_INSTANCES=""

# Función para mostrar uso
usage() {
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Opciones:"
    echo "  -k, --key-path PATH      Ruta al archivo de clave SSH (.pem)"
    echo "  -i, --instances IDS      IDs de instancias separadas por comas (opcional)"
    echo "  -d, --dry-run            Simula la ejecución sin hacer cambios"
    echo "  -h, --help               Muestra esta ayuda"
    echo ""
    echo "Ejemplo:"
    echo "  $0 -k ~/keys/mykey.pem"
    echo "  $0 -k ~/keys/mykey.pem -i i-0e2618a0aed6a3dcd,i-0a838c06fbd8c3b8e"
    exit 1
}

# Procesar argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        -k|--key-path)
            KEY_PATH="$2"
            shift 2
            ;;
        -i|--instances)
            SELECTED_INSTANCES="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
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

# Verificar clave SSH
if [[ -z "$KEY_PATH" ]]; then
    echo -e "${RED}[ERROR]${NC} Debe especificar la ruta al archivo de clave SSH con -k"
    usage
fi

if [[ ! -f "$KEY_PATH" && "$DRY_RUN" != "true" ]]; then
    echo -e "${RED}[ERROR]${NC} No se encontró el archivo de clave: $KEY_PATH"
    exit 1
fi

# Función para obtener IP pública de una instancia
get_instance_ip() {
    local instance_id=$1
    aws ec2 describe-instances --instance-ids $instance_id \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text
}

# Función para desplegar en Linux
deploy_linux() {
    local instance_id=$1
    local instance_name=$2
    local instance_ip=$3
    
    echo -e "${BLUE}[Linux]${NC} Desplegando en $instance_name ($instance_id)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Comandos que se ejecutarían:"
        echo "  scp -i $KEY_PATH $SCRIPT_DIR/install_cloudwatch_agent_linux.sh ec2-user@$instance_ip:/tmp/"
        echo "  scp -i $KEY_PATH $SCRIPT_DIR/cloudwatch-agent-config.json ec2-user@$instance_ip:/tmp/"
        echo "  ssh -i $KEY_PATH ec2-user@$instance_ip 'sudo /tmp/install_cloudwatch_agent_linux.sh'"
        echo "  ssh -i $KEY_PATH ec2-user@$instance_ip 'sudo cp /tmp/cloudwatch-agent-config.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json'"
        echo "  ssh -i $KEY_PATH ec2-user@$instance_ip 'sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json'"
        return 0
    fi
    
    # Copiar scripts
    echo -e "${GREEN}[1/5]${NC} Copiando script de instalación..."
    scp -o StrictHostKeyChecking=no -i "$KEY_PATH" \
        "$SCRIPT_DIR/install_cloudwatch_agent_linux.sh" \
        "ec2-user@$instance_ip:/tmp/"
    
    echo -e "${GREEN}[2/5]${NC} Copiando archivo de configuración..."
    scp -o StrictHostKeyChecking=no -i "$KEY_PATH" \
        "$SCRIPT_DIR/cloudwatch-agent-config.json" \
        "ec2-user@$instance_ip:/tmp/"
    
    # Ejecutar instalación
    echo -e "${GREEN}[3/5]${NC} Ejecutando script de instalación..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" "ec2-user@$instance_ip" \
        "sudo /tmp/install_cloudwatch_agent_linux.sh"
    
    # Copiar configuración
    echo -e "${GREEN}[4/5]${NC} Aplicando configuración..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" "ec2-user@$instance_ip" \
        "sudo cp /tmp/cloudwatch-agent-config.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
    
    # Iniciar servicio
    echo -e "${GREEN}[5/5]${NC} Iniciando CloudWatch Agent..."
    ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" "ec2-user@$instance_ip" \
        "sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
    
    echo -e "${GREEN}[OK]${NC} Despliegue completado en $instance_name"
}

# Función para desplegar en Windows
deploy_windows() {
    local instance_id=$1
    local instance_name=$2
    local instance_ip=$3
    
    echo -e "${BLUE}[Windows]${NC} Desplegando en $instance_name ($instance_id)"
    echo -e "${YELLOW}[INFO]${NC} Para Windows, siga estos pasos manualmente:"
    echo ""
    echo "1. Conéctese a la instancia Windows usando RDP"
    echo "   - IP: $instance_ip"
    echo "   - Usuario: Administrator"
    echo ""
    echo "2. Abra PowerShell como Administrador"
    echo ""
    echo "3. Descargue y ejecute el script de instalación:"
    echo "   Invoke-WebRequest -Uri 'URL_DEL_SCRIPT' -OutFile 'C:\\temp\\install_cloudwatch_agent_windows.ps1'"
    echo "   C:\\temp\\install_cloudwatch_agent_windows.ps1"
    echo ""
    echo "4. Descargue y aplique la configuración:"
    echo "   Invoke-WebRequest -Uri 'URL_DE_CONFIG' -OutFile 'C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\config.json'"
    echo ""
    echo "5. Inicie el servicio:"
    echo "   & \"C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1\" -Action fetch-config -Mode EC2 -ConfigLocation file:\"C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\config.json\""
    echo ""
    echo -e "${YELLOW}[NOTA]${NC} También puede usar Systems Manager Session Manager si está configurado"
}

# Función principal
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Despliegue de CloudWatch Agent${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}MODO DRY-RUN - No se realizarán cambios${NC}"
        echo ""
    fi
    
    # Determinar qué instancias procesar
    if [[ -n "$SELECTED_INSTANCES" ]]; then
        IFS=',' read -ra selected_array <<< "$SELECTED_INSTANCES"
        
        # Procesar instancias seleccionadas
        for selected_id in "${selected_array[@]}"; do
            # Buscar el índice de la instancia
            for i in "${!INSTANCE_IDS[@]}"; do
                if [[ "${INSTANCE_IDS[$i]}" == "$selected_id" ]]; then
                    process_instance "$i"
                    break
                fi
            done
        done
    else
        # Procesar todas las instancias
        for i in "${!INSTANCE_IDS[@]}"; do
            process_instance "$i"
        done
    fi
    
    show_summary
}

# Función para procesar una instancia por índice
process_instance() {
    local index=$1
    local instance_id="${INSTANCE_IDS[$index]}"
    local instance_name="${INSTANCE_NAMES[$index]}"
    local instance_type="${INSTANCE_TYPES[$index]}"
        
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Procesando: $instance_name${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Obtener IP de la instancia
    local instance_ip=$(get_instance_ip $instance_id)
    
    if [[ -z "$instance_ip" || "$instance_ip" == "None" ]]; then
        echo -e "${RED}[ERROR]${NC} No se pudo obtener la IP de $instance_name"
        return
    fi
    
    echo -e "${GREEN}[INFO]${NC} IP: $instance_ip"
    echo -e "${GREEN}[INFO]${NC} Tipo: $instance_type"
    echo ""
    
    # Desplegar según el tipo de SO
    if [[ "$instance_type" == "linux" ]]; then
        deploy_linux "$instance_id" "$instance_name" "$instance_ip"
    elif [[ "$instance_type" == "windows" ]]; then
        deploy_windows "$instance_id" "$instance_name" "$instance_ip"
    fi
    
    echo ""
}

# Agregar resumen al final del main
show_summary() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Resumen${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "Instancias procesadas: ${#INSTANCE_IDS[@]}"
    echo ""
    echo -e "${BLUE}Próximos pasos:${NC}"
    echo "1. Verificar las métricas en CloudWatch Console"
    echo "2. Verificar que las alarmas ahora tienen datos"
    echo "3. Para Windows, completar la instalación manual"
}

# Ejecutar función principal
main