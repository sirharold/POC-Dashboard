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
├── app.py                    # Archivo principal de la aplicación
├── config.yaml              # Configuración central (grupos, colores, ajustes)
├── requirements.txt         # Dependencias de Python
├── Dockerfile              # Configuración para contenedores
├── assets/                 # Estilos CSS personalizados
├── components/             # Componentes reutilizables de UI
│   ├── server_card.py     # Tarjetas de servidor
│   └── group_container.py # Contenedores de grupo
├── utils/                  # Funciones auxiliares
├── ScriptsUtil/           # Scripts de despliegue y configuración
└── docs/                  # Documentación de despliegue
```

## Comandos de Desarrollo

### Ejecutar localmente
```bash
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

### Debug
- `ScriptsUtil/debug_aws.py` - Herramienta para depurar integraciones AWS

## Notas Importantes

1. **Versión**: La versión actual se mantiene en `config.yaml`
2. **Cache**: La aplicación usa un sistema de cache con thread de actualización en background
3. **Múltiples Cuentas AWS**: Soporta asumir roles en diferentes cuentas AWS
4. **Refresh**: El intervalo de actualización es configurable en config.yaml
5. **Alarmas**: Soporta alarmas preventivas y críticas con diferentes colores

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
1. Verificar credenciales AWS configuradas
2. Usar `ScriptsUtil/debug_aws.py` para probar conexiones
3. Revisar logs de CloudWatch para errores
4. Verificar permisos IAM del rol asumido

## Contacto y Documentación
- README.md contiene instrucciones de despliegue
- DEVELOPMENT_HISTORY.md tiene el historial detallado de desarrollo
- La documentación de despliegue está en la carpeta `docs/`