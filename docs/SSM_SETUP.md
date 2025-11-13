# Configuración de Permisos SSM para Descarga de Logs

## Problema
El rol `RecolectorDeDashboard` necesita permisos de AWS Systems Manager (SSM) para leer archivos `available.log` desde las instancias EC2.

Error actual:
```
User: arn:aws:sts::011528297340:assumed-role/RecolectorDeDashboard/StreamlitDashboardSession
is not authorized to perform: ssm:SendCommand
```

## Solución

### ⚠️ Importante: No modificar Trust Policy

La Trust Policy del rol define **quién** puede asumir el rol (debe incluir tu cuenta/usuario).
Los permisos SSM van en una **Permissions Policy** separada.

**Ver guía completa:** `docs/CURRENT_ROLE_SETUP.md`

### Paso 1: Agregar Política de Permisos SSM al Rol

1. Ir a la consola de AWS IAM
2. Buscar el rol: `RecolectorDeDashboard`
3. En la pestaña **"Permissions"** (no "Trust relationships"), hacer clic en "Add permissions" → "Create inline policy"
4. Seleccionar la pestaña "JSON"
5. Copiar y pegar el contenido del archivo: `docs/SSM_PERMISSIONS_POLICY.json`
6. Hacer clic en "Review policy"
7. Nombrar la política: `SSMReadFilesPermissions`
8. Hacer clic en "Create policy"

**Nota:** La Trust Policy debe permanecer sin cambios.

### Paso 2: Verificar SSM Agent en las Instancias

Para que SSM funcione, las instancias EC2 deben tener el SSM Agent instalado y en ejecución.

#### Verificar si el SSM Agent está instalado:

**Linux:**
```bash
sudo systemctl status amazon-ssm-agent
```

**Windows:**
```powershell
Get-Service AmazonSSMAgent
```

#### Instalar SSM Agent (si no está instalado):

**Amazon Linux 2:**
```bash
sudo yum install -y amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

**Ubuntu:**
```bash
sudo snap install amazon-ssm-agent --classic
sudo snap start amazon-ssm-agent
```

**Windows:**
```powershell
# Descargar desde:
# https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/windows_amd64/AmazonSSMAgentSetup.exe
# Ejecutar el instalador
```

### Paso 3: Verificar que las Instancias están Registradas en SSM

En la consola de AWS, ir a:
1. **Systems Manager** → **Fleet Manager**
2. Verificar que las instancias aparezcan en la lista
3. Si no aparecen, verificar:
   - El SSM Agent está corriendo
   - La instancia tiene acceso a internet o VPC endpoints para SSM
   - El IAM Instance Profile tiene permisos SSM (rol `AmazonSSMManagedInstanceCore`)

### Paso 4: Agregar IAM Instance Profile a las Instancias (si no lo tienen)

Si las instancias no tienen un IAM Instance Profile con permisos SSM:

1. Crear un rol con la política: `AmazonSSMManagedInstanceCore`
2. Asociar el rol a las instancias EC2

O usar el rol predeterminado de AWS: `AmazonSSMManagedInstanceCore`

## Resumen de Permisos Necesarios

### Rol RecolectorDeDashboard (Dashboard):
- `ssm:SendCommand`
- `ssm:GetCommandInvocation`
- `ssm:ListCommandInvocations`
- `ssm:DescribeInstanceInformation`

### IAM Instance Profile (Instancias EC2):
- `AmazonSSMManagedInstanceCore` (managed policy)

## Probar la Configuración

Después de aplicar los cambios:

1. Ir al dashboard
2. Navegar a la página de detalles de una instancia
3. En la sección "📄 Visor de Logs SAP (available.log)"
4. Hacer clic en el botón "📥 Descargar"
5. Verificar que el archivo se descargue correctamente

## Troubleshooting

### Error: "Instance is not registered with SSM"
- Verificar que el SSM Agent esté corriendo en la instancia
- Verificar que la instancia tenga un IAM Instance Profile con permisos SSM

### Error: "Timeout waiting for command"
- Verificar conectividad de red (VPC endpoints o internet gateway)
- Aumentar el timeout en el código si es necesario

### Error: "Access Denied"
- Verificar que el rol `RecolectorDeDashboard` tenga los permisos SSM
- Verificar que las instancias tengan el IAM Instance Profile correcto

## Referencias

- [AWS Systems Manager Agent](https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html)
- [Installing SSM Agent](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-install-ssm-agent.html)
- [IAM Permissions for Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/security-iam.html)
