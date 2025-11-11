# Notas de Despliegue - Dashboard EPMAPS POC

**Versión Actual:** v0.6.7

## 📦 Dependencias Requeridas

### Dependencias de Sistema (para Kaleido/PDF)

El proyecto requiere dependencias del sistema para la generación de PDF (conversión de gráficos Plotly a imágenes):

#### Docker (Dockerfile)
```dockerfile
# Ya incluido en el Dockerfile
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y chromium chromium-driver
```

#### macOS
```bash
# No se requieren dependencias adicionales del sistema
# Kaleido incluye su propio runtime
```

### Dependencias de Python

**IMPORTANTE**: Usar `plotly[kaleido]` en vez de instalar `plotly` y `kaleido` por separado.

```bash
pip install -r requirements.txt
```

El `requirements.txt` incluye:
```txt
streamlit
PyYAML
boto3
pandas
streamlit-authenticator
plotly[kaleido]>=6.1.1  # ⚠️ IMPORTANTE: con [kaleido]
reportlab
```

## 🐳 Despliegue con Docker

### Construcción de la Imagen

```bash
# En el directorio raíz del proyecto
docker build -t dashboard-epmaps-poc:latest .
```

El Dockerfile:
- ✅ Instala dependencias del sistema (chromium)
- ✅ Instala dependencias de Python correctamente
- ✅ Configura el entorno para Streamlit
- ✅ Expone el puerto 8501

### Ejecución Local con Docker

```bash
docker run -p 8501:8501 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_DEFAULT_REGION=us-east-1 \
  dashboard-epmaps-poc:latest
```

## ☁️ Despliegue en AWS

### Opción 1: GitHub Actions (Recomendado)

El workflow en `.github/workflows/deploy.yml`:
- ✅ Construye la imagen Docker automáticamente
- ✅ Empuja la imagen a ECR
- ✅ Actualiza la task definition en ECS/Fargate
- ✅ Despliega el servicio

**Trigger**: Push a `main` o `master`

**Requisitos**:
- Secrets configurados en GitHub:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
- Infraestructura AWS existente (ECS Cluster, Service, ALB)

### Opción 2: Script Manual (deploy_fargate.sh)

```bash
# 1. Construir y empujar imagen a ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 687634808667.dkr.ecr.us-east-1.amazonaws.com
docker build -t dashboard-epmaps-poc:latest .
docker tag dashboard-epmaps-poc:latest 687634808667.dkr.ecr.us-east-1.amazonaws.com/dashboard-epmaps-poc:latest
docker push 687634808667.dkr.ecr.us-east-1.amazonaws.com/dashboard-epmaps-poc:latest

# 2. Ejecutar script de deploy
cd ScriptsUtil
./deploy_fargate.sh
```

## 🔍 Verificación Post-Despliegue

### 1. Verificar que las dependencias se instalaron correctamente

Conectarse al contenedor y ejecutar:

```bash
# En el contenedor
python -c "
import plotly
import kaleido
from reportlab.platypus import SimpleDocTemplate
print(f'✅ Plotly version: {plotly.__version__}')
print('✅ Kaleido installed')
print('✅ ReportLab installed')
"
```

### 2. Probar generación de PDF

Acceder a la aplicación y:
1. Ir a "Informe Mensual"
2. Seleccionar rango de fechas
3. Seleccionar "Ping" como tipo de métrica
4. Clic en "🔍 Consultar"
5. Clic en "📄 PDF"
6. Verificar que el PDF se descarga correctamente

### 3. Verificar logs

**AWS CloudWatch Logs:**
```bash
aws logs tail /ecs/streamlit-dashboard-task --follow
```

Buscar errores relacionados con:
- `ImportError: cannot import name 'broadcast_args_to_dicts'` ❌ (no debería aparecer)
- `kaleido` ✅ (debe estar instalado)
- `PDF generation` ✅ (debe funcionar)

## 🚨 Troubleshooting

### Error: `ImportError: cannot import name 'broadcast_args_to_dicts'`

**Causa**: Versiones incompatibles de plotly y kaleido

**Solución**:
```bash
pip uninstall -y plotly kaleido
pip install 'plotly[kaleido]>=6.1.1'
```

**En Docker**: Verificar que `requirements.txt` use `plotly[kaleido]>=6.1.1`

### Error: Kaleido no encuentra chromium

**Causa**: Dependencias del sistema no instaladas

**Solución en Dockerfile**:
```dockerfile
RUN apt-get update && apt-get install -y chromium chromium-driver
```

### Error: PDF no se genera (timeout)

**Causa**: Recursos insuficientes en el contenedor

**Solución**: Aumentar memoria/CPU en task definition:
```json
{
  "cpu": "2048",  // 2 vCPU mínimo recomendado
  "memory": "4096" // 4GB mínimo recomendado
}
```

## 📊 Recursos Requeridos

### Mínimo (para testing)
- CPU: 1 vCPU
- Memoria: 2GB
- Disco: 1GB

### Recomendado (producción)
- CPU: 2 vCPU
- Memoria: 4GB
- Disco: 2GB

### Para generación de PDF
- CPU: +0.5 vCPU adicional
- Memoria: +512MB adicional
- Durante la generación de PDF, el uso de CPU puede aumentar temporalmente

## 📝 Checklist de Despliegue

Antes de hacer deploy a producción:

- [ ] `requirements.txt` usa `plotly[kaleido]>=6.1.1`
- [ ] `Dockerfile` instala dependencias del sistema (chromium)
- [ ] Secrets de AWS configurados en GitHub Actions
- [ ] Task definition tiene recursos suficientes (2 vCPU, 4GB RAM)
- [ ] Tests locales pasaron (`python ScriptsUtil/test_pdf_generation.py`)
- [ ] Build de Docker local exitoso
- [ ] Verificación de imports en contenedor
- [ ] Prueba de generación de PDF en staging

## 🔄 Actualización de Dependencias

Si necesitas actualizar dependencias en el futuro:

```bash
# Actualizar plotly manteniendo kaleido compatible
pip install --upgrade 'plotly[kaleido]'

# Verificar versiones
pip show plotly kaleido

# Probar funcionamiento
python ScriptsUtil/test_pdf_generation.py
```

## 📞 Soporte

Para problemas durante el despliegue:
1. Revisar logs de CloudWatch
2. Ejecutar `test_pdf_generation.py` en el contenedor
3. Verificar versiones de dependencias
4. Consultar `DEVELOPMENT_HISTORY.md` para cambios recientes

---

**Última actualización**: 2025-11-11 (v0.6.7)
**Cambios en esta versión**: Agregada funcionalidad de exportación a PDF
