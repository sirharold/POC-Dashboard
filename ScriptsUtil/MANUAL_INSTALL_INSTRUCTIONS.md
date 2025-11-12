# Instrucciones de Instalación Manual de CloudWatch Agent

## 📋 Resumen de Instancias

| Instancia | Nombre | SO | Método de Conexión |
|-----------|--------|----|-------------------|
| i-0a838c06fbd8c3b8e | SAPLOG2_POC-linux | Linux | Session Manager |
| i-0e2618a0aed6a3dcd | SAPLOG2_POC-win | Windows | Session Manager |
| i-018a476f209209fa8 | SAPLOG2_POC-win2 | Windows | Session Manager |

---

## 🐧 INSTALACIÓN EN LINUX (SAPLOG2_POC-linux)

### Paso 1: Conectarse via Session Manager
```bash
aws ssm start-session --target i-0a838c06fbd8c3b8e
```

**Nota:** Una vez conectado, estarás en una sesión de shell como `ssm-user`. Para ejecutar comandos administrativos, usa `sudo`.

### Paso 2: Descargar CloudWatch Agent
```bash
# Cambiar a directorio temporal
cd /tmp

# Descargar el agente (para Amazon Linux/RHEL)
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm

# Para Ubuntu/Debian, usar instead:
# wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
```

### Paso 3: Instalar CloudWatch Agent
```bash
# Para Amazon Linux/RHEL/CentOS
sudo rpm -U amazon-cloudwatch-agent.rpm

# Para Ubuntu/Debian
# sudo dpkg -i amazon-cloudwatch-agent.deb
```

### Paso 4: Crear archivo de configuración
```bash
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc

# Crear el archivo de configuración
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
          },
          {
            "name": "inodes_free",
            "unit": "Count"
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
```

### Paso 5: Iniciar CloudWatch Agent
```bash
# Aplicar la configuración e iniciar el servicio
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

### Paso 6: Verificar el estado
```bash
# Verificar que el servicio está ejecutándose
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a query \
    -m ec2

# Ver logs del agente
sudo tail -f /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
```

---

## 🪟 INSTALACIÓN EN WINDOWS

### Para SAPLOG2_POC-win

#### Paso 1: Conectarse via Session Manager
```bash
aws ssm start-session --target i-0e2618a0aed6a3dcd
```

#### Paso 2: Cambiar a PowerShell en la sesión
Una vez conectado, cambiar a PowerShell:
```cmd
powershell
```

#### Paso 3: Configurar TLS y descargar el agente
```powershell
# Configurar TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Crear directorio temporal
New-Item -ItemType Directory -Force -Path C:\temp

# Descargar CloudWatch Agent
$downloadUrl = "https://s3.amazonaws.com/amazoncloudwatch-agent/windows/amd64/latest/amazon-cloudwatch-agent.msi"
Invoke-WebRequest -Uri $downloadUrl -OutFile "C:\temp\amazon-cloudwatch-agent.msi"
```

#### Paso 4: Instalar CloudWatch Agent
```powershell
# Instalar silenciosamente
Start-Process msiexec.exe -ArgumentList "/i C:\temp\amazon-cloudwatch-agent.msi /quiet" -Wait
```

#### Paso 5: Crear archivo de configuración
```powershell
# Crear el archivo de configuración
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

# Guardar el archivo de configuración
$configPath = "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\config.json"
$configContent | Out-File -FilePath $configPath -Encoding UTF8
```

#### Paso 6: Iniciar CloudWatch Agent
```powershell
# Aplicar configuración e iniciar servicio
& "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\amazon-cloudwatch-agent-ctl.ps1" `
    -Action fetch-config `
    -Mode EC2 `
    -ConfigLocation "file:${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\config.json"

# Iniciar el servicio
Start-Service -Name "AmazonCloudWatchAgent"
```

#### Paso 7: Verificar instalación
```powershell
# Verificar estado del servicio
Get-Service -Name "AmazonCloudWatchAgent"

# Ver logs del agente
Get-Content "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\Logs\amazon-cloudwatch-agent.log" -Tail 20
```

### Para SAPLOG2_POC-win2

#### Paso 1: Conectarse via Session Manager
```bash
aws ssm start-session --target i-018a476f209209fa8
```

#### Paso 2: Cambiar a PowerShell en la sesión
Una vez conectado, cambiar a PowerShell:
```cmd
powershell
```

#### Pasos 3-7: Seguir los mismos pasos que SAPLOG2_POC-win (arriba)

---

## 🔍 VERIFICACIÓN POST-INSTALACIÓN

### Verificar en AWS CloudWatch Console

1. **Ir a CloudWatch Console**
   - https://console.aws.amazon.com/cloudwatch/

2. **Verificar métricas personalizadas**
   - Ir a "Metrics" → "CWAgent"
   - Deberías ver métricas para tus instancias

3. **Verificar alarmas**
   - Las alarmas de disco y memoria deberían cambiar de "INSUFFICIENT_DATA" a "OK" o "ALARM"

### Comandos útiles para troubleshooting

#### Linux:
```bash
# Estado del servicio
sudo systemctl status amazon-cloudwatch-agent

# Reiniciar servicio
sudo systemctl restart amazon-cloudwatch-agent

# Ver logs en tiempo real
sudo tail -f /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
```

#### Windows:
```powershell
# Estado del servicio
Get-Service AmazonCloudWatchAgent

# Reiniciar servicio
Restart-Service AmazonCloudWatchAgent

# Ver logs
Get-Content "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent\Logs\amazon-cloudwatch-agent.log" -Tail 50 -Wait
```

---

## ⚠️ REQUISITOS IMPORTANTES

### 1. IAM Role
Las instancias EC2 deben tener un IAM Role con estos permisos:
- `CloudWatchAgentServerPolicy`
- `AmazonSSMManagedInstanceCore` (para Session Manager)

### 2. Security Groups
- **Linux**: Puerto 22 (SSH) abierto desde tu IP
- **Windows**: Puerto 3389 (RDP) abierto desde tu IP

### 3. Métricas esperadas
Después de la instalación, deberías ver estas métricas en CloudWatch:
- `CWAgent/cpu_usage_active`
- `CWAgent/disk_used_percent`
- `CWAgent/mem_used_percent`

---

## 📞 CONTACTO Y SOPORTE

Si encuentras problemas:
1. Verificar los logs del agente
2. Verificar permisos IAM
3. Verificar conectividad de red
4. Reiniciar el servicio CloudWatch Agent

¡Las alarmas deberían empezar a recibir datos en 5-10 minutos después de la instalación!