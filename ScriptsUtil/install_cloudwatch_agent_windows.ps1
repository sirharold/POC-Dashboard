# Script para instalar CloudWatch Agent en Windows
# Autor: Sistema automatizado
# Fecha: Get-Date

# Verificar que se ejecuta como administrador
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Write-Host "[ERROR] Este script debe ejecutarse como Administrador" -ForegroundColor Red
    Write-Host "Por favor, ejecute PowerShell como Administrador y vuelva a intentar." -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Instalación de CloudWatch Agent en Windows" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Configurar TLS 1.2 para las descargas
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# URL de descarga del CloudWatch Agent
$downloadUrl = "https://s3.amazonaws.com/amazoncloudwatch-agent/windows/amd64/latest/amazon-cloudwatch-agent.msi"
$installerPath = "$env:TEMP\amazon-cloudwatch-agent.msi"

# Paso 1: Descargar CloudWatch Agent
Write-Host "[PASO 1/4] Descargando CloudWatch Agent..." -ForegroundColor Blue
try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "[OK] Descarga completada" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] No se pudo descargar CloudWatch Agent: $_" -ForegroundColor Red
    exit 1
}

# Paso 2: Instalar CloudWatch Agent
Write-Host "[PASO 2/4] Instalando CloudWatch Agent..." -ForegroundColor Blue
try {
    $arguments = "/i `"$installerPath`" /quiet"
    $process = Start-Process msiexec.exe -ArgumentList $arguments -Wait -PassThru
    
    if ($process.ExitCode -eq 0) {
        Write-Host "[OK] CloudWatch Agent instalado exitosamente" -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] Error durante la instalación. Código de salida: $($process.ExitCode)" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "[ERROR] Error durante la instalación: $_" -ForegroundColor Red
    exit 1
}

# Paso 3: Verificar la instalación
Write-Host "[PASO 3/4] Verificando la instalación..." -ForegroundColor Blue
$agentPath = "${Env:ProgramFiles}\Amazon\AmazonCloudWatchAgent"
$configPath = "$agentPath\config.json"

if (Test-Path $agentPath) {
    Write-Host "[OK] CloudWatch Agent instalado en: $agentPath" -ForegroundColor Green
}
else {
    Write-Host "[ERROR] No se encontró la instalación de CloudWatch Agent" -ForegroundColor Red
    exit 1
}

# Verificar si existe archivo de configuración
if (-not (Test-Path $configPath)) {
    Write-Host "[ADVERTENCIA] No se encontró archivo de configuración" -ForegroundColor Yellow
    Write-Host "[INFO] Ejecute el script de configuración o copie el archivo manualmente" -ForegroundColor Yellow
}

# Paso 4: Estado del servicio
Write-Host "[PASO 4/4] Verificando estado del servicio..." -ForegroundColor Blue

# Verificar si el servicio existe
$service = Get-Service -Name "AmazonCloudWatchAgent" -ErrorAction SilentlyContinue

if ($service) {
    Write-Host "Estado del servicio: $($service.Status)" -ForegroundColor Cyan
    
    if ($service.Status -ne "Running" -and (Test-Path $configPath)) {
        Write-Host "Iniciando el servicio..." -ForegroundColor Yellow
        try {
            & "$agentPath\amazon-cloudwatch-agent-ctl.ps1" `
                -Action fetch-config `
                -Mode EC2 `
                -ConfigLocation "file:$configPath"
            
            Start-Service -Name "AmazonCloudWatchAgent"
            Write-Host "[OK] Servicio iniciado" -ForegroundColor Green
        }
        catch {
            Write-Host "[ADVERTENCIA] No se pudo iniciar el servicio automáticamente" -ForegroundColor Yellow
        }
    }
}
else {
    Write-Host "[ERROR] No se encontró el servicio AmazonCloudWatchAgent" -ForegroundColor Red
}

# Limpiar archivo temporal
Remove-Item -Path $installerPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[COMPLETO] Instalación finalizada" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Blue
Write-Host "1. Copiar el archivo de configuración a: $configPath"
Write-Host "2. Iniciar el servicio con el siguiente comando:"
Write-Host "   & `"$agentPath\amazon-cloudwatch-agent-ctl.ps1`" -Action fetch-config -Mode EC2 -ConfigLocation file:$configPath" -ForegroundColor Cyan
Write-Host "3. Verificar las métricas en CloudWatch Console"
Write-Host ""

# Mostrar información adicional
Write-Host "Para verificar el estado del servicio:" -ForegroundColor Blue
Write-Host "   Get-Service AmazonCloudWatchAgent" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para ver los logs del agente:" -ForegroundColor Blue
Write-Host "   Get-Content `"$agentPath\Logs\amazon-cloudwatch-agent.log`" -Tail 50" -ForegroundColor Cyan