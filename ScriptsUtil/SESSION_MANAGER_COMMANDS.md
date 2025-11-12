# Comandos Rápidos - CloudWatch Agent via Session Manager

## 🚀 Comandos de Conexión

### Linux (SAPLOG2_POC-linux)
```bash
aws ssm start-session --target i-0a838c06fbd8c3b8e
```

### Windows (SAPLOG2_POC-win)
```bash
aws ssm start-session --target i-0e2618a0aed6a3dcd
```

### Windows (SAPLOG2_POC-win2)
```bash
aws ssm start-session --target i-018a476f209209fa8
```

---

## 🐧 LINUX - Comandos en Bloque

### Una vez conectado a SAPLOG2_POC-linux:

```bash
# Descargar e instalar CloudWatch Agent
cd /tmp
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U amazon-cloudwatch-agent.rpm

# Crear directorio de configuración
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc

# Crear archivo de configuración
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json > /dev/null <<'EOF'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {
            "name": "cpu_usage_idle",
            "rename": "CPU_USAGE_IDLE",
            "unit": "Percent"
          },
          "cpu_usage_active"
        ],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {
            "name": "used_percent",
            "rename": "disk_used_percent",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "*"
        ],
        "ignore_file_system_types": [
          "devtmpfs",
          "tmpfs"
        ]
      },
      "mem": {
        "measurement": [
          {
            "name": "mem_used_percent",
            "rename": "mem_used_percent",
            "unit": "Percent"
          },
          "mem_available_percent",
          "mem_used",
          "mem_total"
        ],
        "metrics_collection_interval": 60
      }
    },
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}",
      "InstanceType": "${aws:InstanceType}",
      "ImageId": "${aws:ImageId}"
    }
  }
}
EOF

# Iniciar CloudWatch Agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Verificar estado
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a query \
    -m ec2
```

---

## 🪟 WINDOWS - Comandos en Bloque

### Una vez conectado a SAPLOG2_POC-win o SAPLOG2_POC-win2:

Primero cambiar a PowerShell:
```cmd
powershell
```

Luego ejecutar estos comandos PowerShell:

```powershell
# Configurar TLS y crear directorio temporal
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Force -Path C:\temp

# Descargar CloudWatch Agent
$downloadUrl = "https://s3.amazonaws.com/amazoncloudwatch-agent/windows/amd64/latest/amazon-cloudwatch-agent.msi"
Invoke-WebRequest -Uri $downloadUrl -OutFile "C:\temp\amazon-cloudwatch-agent.msi"

# Instalar CloudWatch Agent
Start-Process msiexec.exe -ArgumentList "/i C:\temp\amazon-cloudwatch-agent.msi /quiet" -Wait

# Esperar a que la instalación complete
Start-Sleep -Seconds 30

# Crear archivo de configuración
$configContent = @'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "LogicalDisk": {
        "measurement": [
          {
            "name": "% Free Space",
            "rename": "disk_free_percent",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "*"
        ]
      },
      "Memory": {
        "measurement": [
          {
            "name": "% Committed Bytes In Use",
            "rename": "mem_used_percent",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      },
      "Processor": {
        "measurement": [
          {
            "name": "% Processor Time",
            "rename": "cpu_usage_active",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "_Total"
        ]
      }
    },
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}",
      "InstanceType": "${aws:InstanceType}",
      "ImageId": "${aws:ImageId}"
    }
  }
}
'@

# Guardar archivo de configuración
$configPath = "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\config.json"
$configContent | Out-File -FilePath $configPath -Encoding UTF8

# Aplicar configuración e iniciar servicio
& "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\amazon-cloudwatch-agent-ctl.ps1" `
    -Action fetch-config `
    -Mode EC2 `
    -ConfigLocation "file:${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\config.json"

# Iniciar servicio
Start-Service -Name "AmazonCloudWatchAgent"

# Verificar estado
Get-Service -Name "AmazonCloudWatchAgent"
```

---

## ⚡ Comandos de Verificación Rápida

### Linux:
```bash
# Estado del servicio
sudo systemctl status amazon-cloudwatch-agent

# Ver logs
sudo tail -20 /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log

# Reiniciar si es necesario
sudo systemctl restart amazon-cloudwatch-agent
```

### Windows:
```powershell
# Estado del servicio
Get-Service AmazonCloudWatchAgent

# Ver logs
Get-Content "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\Logs\amazon-cloudwatch-agent.log" -Tail 20

# Reiniciar si es necesario
Restart-Service AmazonCloudWatchAgent
```

---

## 🔍 Verificación en CloudWatch Console

1. Ir a: https://console.aws.amazon.com/cloudwatch/
2. Metrics → CWAgent
3. Buscar métricas para tus instancias
4. Las alarmas deberían cambiar de "INSUFFICIENT_DATA" a "OK" en 5-10 minutos

---

## ⚠️ Troubleshooting

Si Session Manager no se conecta:
```bash
# Verificar que las instancias tienen el SSM Agent
aws ssm describe-instance-information --query "InstanceInformationList[?InstanceId=='i-0a838c06fbd8c3b8e']"

# Verificar IAM roles
aws iam list-attached-role-policies --role-name EC2-SSM-Role
```

Si CloudWatch Agent no funciona:
1. Verificar permisos IAM (CloudWatchAgentServerPolicy)
2. Verificar conectividad a internet desde las instancias
3. Reiniciar el servicio del agente