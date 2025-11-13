# Instrucciones para Claude - Dashboard EPMAPS POC

## Información del Proyecto
Este es un dashboard de monitoreo de máquinas virtuales construido con Streamlit y desplegado en AWS. El proyecto se integra con CloudWatch para obtener métricas y alarmas en tiempo real.

## Stack Tecnológico
- **Framework**: Streamlit (Python)
- **Visualización**: Plotly
- **Cloud**: AWS (EC2, CloudWatch, App Runner, Fargate)
- **Contenedores**: Docker
- **CI/CD**: GitHub Actions

## Estructura del Proyecto
```
.
├── app.py                      # Punto de entrada de la aplicación
├── dashboard_manager.py        # Gestor principal y router de páginas
├── config.yaml                 # Configuración central (grupos, colores, versión)
├── requirements.txt            # Dependencias de Python
├── Dockerfile                  # Configuración para contenedores
├── assets/                     # Estilos CSS personalizados
├── services/                   # Lógica de negocio y servicios
│   ├── aws_service.py         # Servicio para integraciones con AWS
│   └── sap_service.py         # Servicio para datos de SAP
├── ui_components/              # Componentes de interfaz de usuario
│   ├── dashboard_ui.py        # Dashboard principal de monitoreo
│   ├── detail_ui.py           # Página de detalles de instancia
│   ├── alarm_report_ui.py     # Página de reporte de alarmas
│   └── monthly_report_ui.py   # Página de informe mensual
├── utils/                      # Funciones auxiliares
│   ├── helpers.py             # Funciones de utilidad general
│   ├── auth.py                # Autenticación de usuarios
│   ├── availability_calculator.py  # Cálculo de disponibilidad con schedules
│   └── parameters_loader.py   # Cargador de parámetros de VMs desde JSON
├── Parameters/                 # Archivos JSON con configuración de VMs
│   ├── Params_Prod_A.json     # Configuración VMs producción grupo A
│   ├── Params_Prod_B.json     # Configuración VMs producción grupo B
│   ├── Params_QADEV_A.json    # Configuración VMs QA/Dev grupo A
│   └── Params_QADEV_B.json    # Configuración VMs QA/Dev grupo B
├── ScriptsUtil/                # Scripts de despliegue y debug
│   ├── deploy_*.sh            # Scripts de despliegue
│   ├── test_aws_connection.py # Test de conexión AWS
│   ├── analyze_alarm_dimensions.py  # Análisis de alarmas
│   ├── debug_alarm_matching.py      # Debug de matching de alarmas
│   ├── debug_ping_metrics.py        # Debug de métricas CloudWatch
│   └── test_availability_calculator.py  # Tests de disponibilidad
└── docs/                       # Documentación de despliegue
```

## Comandos de Desarrollo

### Setup AWS Local
```bash
# Configurar AWS profile
aws configure --profile aquito-role

# Exportar profile para desarrollo local
export AWS_PROFILE=aquito-role

# Verificar conexión AWS
python ScriptsUtil/test_aws_connection.py
```

### Ejecutar localmente
```bash
# Asegurarse de tener el AWS profile exportado
export AWS_PROFILE=aquito-role

# Ejecutar aplicación
streamlit run app.py
```

### Instalar dependencias
```bash
pip install -r requirements.txt
```

### Docker
```bash
# Construir imagen
docker build -t epmaps-dashboard .

# Ejecutar contenedor
docker run -p 8501:8501 epmaps-dashboard
```

### Verificación de código
Como es un proyecto Python sin herramientas de linting configuradas, se recomienda:
```bash
# Verificar sintaxis Python
python -m py_compile app.py components/*.py utils/*.py

# Para análisis estático (si se instala)
pip install flake8
flake8 app.py components/ utils/
```

## Convenciones del Proyecto

### Código Python
- Usar type hints cuando sea posible
- Seguir PEP 8 para estilo de código
- Documentar funciones con docstrings
- Mantener funciones pequeñas y enfocadas

### Configuración
- Toda la configuración debe ir en `config.yaml`
- No hardcodear valores, usar el archivo de configuración
- Los grupos de servidores y sus estilos se definen en config.yaml

### Componentes Streamlit
- Los componentes reutilizables van en `components/`
- Usar st.container() para agrupar elementos
- Aplicar CSS mediante st.markdown() con unsafe_allow_html=True

### AWS Integration
- Usar boto3 para todas las integraciones con AWS
- Manejar errores de AWS gracefully
- Implementar retry logic para llamadas a la API
- Cache de datos para mejorar performance

### Git Commits
- Mensajes descriptivos en inglés
- Formato: "Add/Update/Fix/Refactor + descripción"
- Ejemplo: "Add support for preventive alarms"

### Documentación
- **IMPORTANTE**: Con cada cambio se debe mantener DEVELOPMENT_HISTORY.md actualizado
- Documentar todos los cambios significativos, problemas resueltos y decisiones técnicas
- Incluir fecha y descripción detallada de los cambios realizados

## Scripts Importantes

### Despliegue
- `ScriptsUtil/deploy_cloudwatch_agent.sh` - Instala el agente de CloudWatch
- `ScriptsUtil/deploy_fargate.sh` - Despliega en AWS Fargate
- `ScriptsUtil/create_cloudwatch_alarms.sh` - Crea alarmas de CloudWatch

### Debug y Análisis
- `ScriptsUtil/test_aws_connection.py` - Verifica conexión AWS y permisos de rol
- `ScriptsUtil/analyze_alarm_dimensions.py` - Analiza dimensiones de todas las alarmas de CloudWatch
- `ScriptsUtil/debug_alarm_matching.py` - Debug de matching de alarmas por instancia
- `ScriptsUtil/debug_ping_metrics.py` - Debug de métricas CloudWatch (namespace, dimensiones)
- `ScriptsUtil/test_availability_calculator.py` - Tests de cálculo de disponibilidad con schedules
- `ScriptsUtil/debug_aws.py` - Herramienta general para depurar integraciones AWS

## Notas Importantes

1. **Versión**: La versión actual se mantiene en `config.yaml` (actualmente v0.6.7)
2. **Cache**: La aplicación usa un sistema de cache con thread de actualización en background
3. **Múltiples Cuentas AWS**: Soporta asumir roles en diferentes cuentas AWS
4. **Refresh**: El intervalo de actualización es configurable en config.yaml
5. **Alarmas**: Soporta alarmas preventivas y críticas con diferentes colores
6. **Páginas Disponibles**:
   - Dashboard principal: Monitoreo en tiempo real
   - Página de detalles: Vista detallada de instancia
   - Reporte de alarmas: Análisis global de alarmas
   - Informe mensual: Reportes históricos con selección de fecha, métricas de ping, y exportación a PDF
7. **Filtrado de Alarmas**: Usa matching basado en dimensiones (InstanceId y Server) para precisión
8. **Cálculo de Disponibilidad**: La librería `utils/availability_calculator.py` considera schedules de mantenimiento:
   - **Weekends**: Apagado viernes 21:00 - lunes 10:00
   - **Nights**: Apagado diariamente 21:00 - 06:00
   - **BusinessHours**: Solo disponible L-V 08:00-18:00
   - El cálculo excluye el downtime programado de las métricas de disponibilidad
9. **Tags de Schedule**: Para que una instancia use cálculo inteligente de disponibilidad:
   - Agregar tag `Schedule` (case sensitive, con mayúscula) con valor: `Weekends`, `Nights`, o `BusinessHours`
   - El AWS service extrae automáticamente este tag y lo usa en los reportes
10. **Exportación a PDF**: Los informes mensuales se pueden exportar a PDF:
   - Botón "📄 PDF" junto al título del reporte
   - Formato landscape (11" x 8.5") con 4 columnas
   - Incluye título con fechas y gráficos de disponibilidad
   - Usa `plotly[kaleido]` para convertir Plotly a imágenes y `reportlab` para generar PDF
   - **Importante**: Instalar usando `pip install 'plotly[kaleido]>=6.1.1'` para evitar problemas de compatibilidad
   - Versiones compatibles: Plotly 6.4.0 + Kaleido 1.2.0
11. **Descarga de Logs SAP**: La página de detalles incluye un visor de logs SAP:
   - Muestra archivos `available.log` configurados en `Parameters/*.json`
   - Usa AWS Systems Manager (SSM) para leer archivos remotos desde las instancias
   - Botón de descarga para cada archivo con formato: `AvailableLog_SERVERNAME_PATH_YYYYMMDD_HHMM.log`
   - Soporta tanto instancias Linux (usando `cat`) como Windows (usando PowerShell `Get-Content`)
   - Los archivos de parámetros deben incluir: `instance_id`, `name`, `os_type`, y `paths` (array de rutas)
   - **Requisitos**:
     - SSM Agent instalado en las instancias
     - Rol `RecolectorDeDashboard` con permisos SSM
     - IAM Instance Profile en las instancias con `AmazonSSMManagedInstanceCore`
     - Ver `docs/SSM_SETUP.md` para instrucciones completas de configuración

## Tareas Comunes

### Agregar un nuevo grupo de servidores
1. Editar `config.yaml` y agregar el grupo en la sección `groups`
2. Definir la clase CSS correspondiente si es necesaria
3. Reiniciar la aplicación

### Modificar estilos visuales
1. Los estilos principales están en `assets/styles.css`
2. Los colores de estado están definidos en `config.yaml`
3. Usar las clases CSS existentes cuando sea posible

### Debugging de problemas AWS
1. Verificar credenciales AWS configuradas: `aws sts get-caller-identity`
2. Probar conexión y permisos de rol: `python ScriptsUtil/test_aws_connection.py`
3. Analizar dimensiones de alarmas: `python ScriptsUtil/analyze_alarm_dimensions.py`
4. Debug de matching de alarmas específicas: `python ScriptsUtil/debug_alarm_matching.py <instance_name>`
5. Revisar logs de CloudWatch para errores
6. Verificar Trust Policy del rol RecolectorDeDashboard incluya el rol local

### Configuración de SSM para descarga de logs
Si encuentras error: `User is not authorized to perform: ssm:SendCommand`

**Solución:**
1. Ver documentación completa en `docs/SSM_SETUP.md`
2. Agregar política SSM al rol `RecolectorDeDashboard` usando `docs/SSM_PERMISSIONS_POLICY.json`
3. Verificar que las instancias tengan SSM Agent instalado
4. Verificar que las instancias tengan IAM Instance Profile con `AmazonSSMManagedInstanceCore`

### Troubleshooting PDF Generation
Si encuentras error: `ImportError: cannot import name 'broadcast_args_to_dicts' from 'plotly.io._utils'`

**Solución:**
```bash
# Desinstalar kaleido independiente si está instalado
pip uninstall -y kaleido

# Reinstalar plotly con kaleido bundled
pip install 'plotly[kaleido]>=6.1.1'

# Verificar instalación
python ScriptsUtil/test_pdf_generation.py
```

**Versiones compatibles verificadas:**
- Plotly 6.4.0
- Kaleido 1.2.0 (instalado automáticamente por plotly[kaleido])
- ReportLab 4.4.4

### Agregar nuevos archivos de logs SAP
1. Editar el archivo JSON correspondiente en `Parameters/`
2. Agregar el `instance_id` si la VM no existe en el archivo
3. Agregar la ruta del archivo `available.log` al array `paths`
4. Verificar que el SSM Agent esté instalado en la instancia
5. No es necesario reiniciar la aplicación, los cambios se cargan dinámicamente

Ejemplo de estructura JSON:
```json
{
  "vms": [
    {
      "instance_id": "i-1234567890abcdef0",
      "name": "SRVERPTEST",
      "os_type": "linux",
      "paths": [
        "/usr/sap/ERP/D00/work/available.log",
        "/usr/sap/ERP/ASCS01/work/available.log"
      ]
    }
  ]
}
```

### Setup de permisos AWS local
Para desarrollo local, el rol RecolectorDeDashboard debe tener en su Trust Policy:
```json
{
  "Principal": {
    "AWS": [
      "arn:aws:iam::687634808667:root",
      "arn:aws:iam::011528297340:role/morrisopazo"
    ]
  }
}
```

## Contacto y Documentación
- README.md contiene instrucciones de despliegue
- DEVELOPMENT_HISTORY.md tiene el historial detallado de desarrollo
- La documentación de despliegue está en la carpeta `docs/`