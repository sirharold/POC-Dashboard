#!/bin/bash

# Script para instalar CloudWatch Agent en Linux
# Autor: Sistema automatizado
# Fecha: $(date)

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Instalación de CloudWatch Agent en Linux${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}[ERROR]${NC} Este script debe ejecutarse como root (sudo)"
    exit 1
fi

# Detectar la distribución
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}[ERROR]${NC} No se pudo detectar la distribución de Linux"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} Sistema detectado: $OS $VER"

# Descargar CloudWatch Agent
echo -e "${BLUE}[PASO 1/4]${NC} Descargando CloudWatch Agent..."

if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    DOWNLOAD_URL="https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"
    PACKAGE_FILE="/tmp/amazon-cloudwatch-agent.deb"
    wget -q $DOWNLOAD_URL -O $PACKAGE_FILE
    
    echo -e "${BLUE}[PASO 2/4]${NC} Instalando CloudWatch Agent..."
    dpkg -i $PACKAGE_FILE
    
elif [[ "$OS" == "rhel" ]] || [[ "$OS" == "centos" ]] || [[ "$OS" == "amzn" ]]; then
    DOWNLOAD_URL="https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm"
    PACKAGE_FILE="/tmp/amazon-cloudwatch-agent.rpm"
    wget -q $DOWNLOAD_URL -O $PACKAGE_FILE
    
    echo -e "${BLUE}[PASO 2/4]${NC} Instalando CloudWatch Agent..."
    rpm -U $PACKAGE_FILE
else
    echo -e "${RED}[ERROR]${NC} Distribución no soportada: $OS"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} CloudWatch Agent instalado exitosamente"

# Crear directorio de configuración si no existe
echo -e "${BLUE}[PASO 3/4]${NC} Configurando CloudWatch Agent..."
mkdir -p /opt/aws/amazon-cloudwatch-agent/etc

# Verificar si existe un archivo de configuración
CONFIG_FILE="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}[ADVERTENCIA]${NC} No se encontró archivo de configuración"
    echo -e "${YELLOW}[INFO]${NC} Ejecute el script de configuración o copie el archivo manualmente"
fi

# Verificar el estado del servicio
echo -e "${BLUE}[PASO 4/4]${NC} Verificando estado del servicio..."

# No iniciar el servicio automáticamente si no hay configuración
if [ -f "$CONFIG_FILE" ]; then
    # Aplicar la configuración
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
        -a fetch-config \
        -m ec2 \
        -s \
        -c file:$CONFIG_FILE
    
    echo -e "${GREEN}[OK]${NC} CloudWatch Agent configurado y en ejecución"
else
    echo -e "${YELLOW}[INFO]${NC} CloudWatch Agent instalado pero no iniciado"
    echo -e "${YELLOW}[INFO]${NC} Para iniciar el servicio después de configurar:"
    echo -e "  sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \\"
    echo -e "    -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
fi

# Mostrar estado del servicio
echo ""
echo -e "${BLUE}Estado del servicio:${NC}"
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a query \
    -m ec2

echo ""
echo -e "${GREEN}[COMPLETO]${NC} Instalación finalizada"
echo ""
echo -e "${BLUE}Próximos pasos:${NC}"
echo "1. Copiar el archivo de configuración a $CONFIG_FILE"
echo "2. Iniciar el servicio con el comando mostrado arriba"
echo "3. Verificar las métricas en CloudWatch Console"