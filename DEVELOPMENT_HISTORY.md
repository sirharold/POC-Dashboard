# Histórico de Desarrollo - Dashboard EPMAPS POC

Este archivo documenta todas las instrucciones, cambios y evolución del proyecto para poder retomar el desarrollo en cualquier punto.

## Contexto del Proyecto

**Objetivo**: Crear una aplicación con Streamlit que viva dentro de AWS para monitoreo de salud de máquinas virtuales, con capacidad de expansión futura para reportes, tendencias, etc.

**Tecnologías**:
- Streamlit (framework principal)
- Boto3 (AWS SDK para Python)
- Docker (Contenedores)
- AWS App Runner (Despliegue Serverless)

## Registro de Desarrollo

### 2025-09-10 - Versión 5.0 (Beta 1): Modernización y Preparación para Despliegue

#### Resumen
En esta fase, la aplicación fue refactorizada en profundidad para eliminar dependencias de herramientas de línea de comandos (`aws-cli`) y adoptar una arquitectura moderna, robusta y portable, lista para un despliegue profesional en la nube.

#### Cambios Implementados

1.  **Refactorización a `boto3`**:
    *   Se reemplazaron todas las llamadas a `subprocess` que ejecutaban `aws-cli`.
    *   Toda la comunicación con AWS (EC2 y CloudWatch) ahora se realiza de forma nativa en Python a través de la librería `boto3`.
    *   **Beneficios:** Mayor rendimiento, código más limpio, mejor manejo de errores y eliminación de una dependencia externa del entorno de ejecución.

2.  **Contenerización con Docker**:
    *   Se añadió un `Dockerfile` a la raíz del proyecto.
    *   Este archivo permite empaquetar la aplicación y todas sus dependencias en un contenedor estándar, garantizando que funcione de la misma manera en cualquier entorno (local o en la nube).

3.  **Nueva Estrategia de Despliegue con AWS App Runner**:
    *   Se definió una nueva estrategia de despliegue recomendada que utiliza AWS App Runner, un servicio serverless.
    *   **Beneficios:** Costo-eficiencia (pago por uso, escala a cero), totalmente gestionado por AWS, y despliegue continuo desde el repositorio de código.

4.  **Creación de Documentación de Despliegue**:
    *   Se creó un nuevo directorio `docs/`.
    *   Se añadieron dos guías de despliegue detalladas:
        *   `deploy_using_app_runner.md` (Recomendada)
        *   `deploy_using_ec2instance.md` (Alternativa)

5.  **Mejoras de Navegación y UI**:
    *   Se corrigieron errores de navegación a las páginas de detalle.
    *   Se reestructuró el directorio `pages/` para ocultar las páginas de detalle de la barra lateral, limpiando el menú principal.
    *   La aplicación ahora carga directamente en la página de "Producción" para una mejor experiencia de usuario.

#### Decisión de Arquitectura
Se abandona el uso de `aws-cli` en favor de `boto3` para alinear el proyecto con las mejores prácticas de desarrollo de aplicaciones en la nube, habilitando despliegues en contenedores y mejorando la mantenibilidad general del código.

### 2025-09-10 - Inicio del Proyecto

#### Requerimientos Iniciales
El usuario solicitó crear un POC con las siguientes características:

1. **Página Principal**:
   - Título: "Dashboard POC"
   - Grupo: "SAP ISU PRODUCCIÓN"
   - 3 servidores virtuales:
     - SRVISUASCS (estado verde)
     - SRVISUPRD (estado rojo)
     - SRVISUPRDDB (estado amarillo)
   - Indicadores tipo semáforo para mostrar estado
   - Contador de alertas totales
   - Gráfico tipo pie mostrando alertas críticas/advertencias/ok

2. **Página de Detalle** (al hacer clic en una VM):
   - Columna 1: Listado gráfico de alarmas (luz + nombre)
   - Columna 2: 
     - Filtro de tiempo (5min, 15min, 30min, 1h, 3h, 6h, 12h)
     - Indicadores de CPU (1 por núcleo)
     - Indicador de RAM
     - Indicadores de discos (5 discos)

#### Implementación Realizada

**Archivos creados**:
1. `app.py` - Aplicación principal con toda la lógica
2. `requirements.txt` - Dependencias (streamlit, plotly)

**Características implementadas**:
- ✅ Dashboard principal con 3 VMs
- ✅ Estados de semáforo (verde, rojo, amarillo) con indicadores visuales
- ✅ Contadores de alertas totales
- ✅ Gráficos de pie para distribución de alertas
- ✅ Navegación a página de detalle por VM
- ✅ Listado de alarmas con indicadores visuales
- ✅ Filtro de tiempo
- ✅ Métricas de CPU (4 núcleos)
- ✅ Métrica de RAM
- ✅ Métricas de 5 discos duros

**Decisiones técnicas**:
- Uso de `st.session_state` para manejar navegación entre vistas
- Datos hardcodeados para el POC
- Diseño responsive con columnas de Streamlit
- Plotly para gráficos de pie compactos
- CSS inline para personalizar apariencia de semáforos

## Próximos Pasos Sugeridos

1. **Integración con AWS**:
   - Configurar despliegue en EC2/ECS/Lambda
   - Implementar autenticación
   - Conectar con CloudWatch para métricas reales

2. **Mejoras de Funcionalidad**:
   - Agregar persistencia de datos
   - Implementar actualización en tiempo real
   - Añadir módulo de reportes
   - Implementar tendencias históricas

3. **Mejoras de UI/UX**:
   - Tema oscuro/claro
   - Notificaciones push para alertas críticas
   - Dashboard personalizable

## Notas para Retomar el Desarrollo

Para continuar el desarrollo:
1. Instalar dependencias: `pip install -r requirements.txt`
2. Ejecutar aplicación: `streamlit run app.py`
3. Revisar este archivo para entender el contexto
4. Consultar README.md para ver el changelog actualizado

## Estructura del Proyecto

```
POC/
├── app.py                    # Aplicación principal
├── requirements.txt          # Dependencias
├── DEVELOPMENT_HISTORY.md    # Este archivo
└── README.md                # Documentación y changelog
```

### 2025-09-10 - Segunda Iteración: Múltiples Grupos de Servidores

#### Nuevos Requerimientos
El usuario solicitó agregar un segundo grupo de servidores:
- Grupo: "SAP ERP"
- 2 servidores:
  - SRVERPPRD (estado verde)
  - SRVSAPERPBDD (estado amarillo)
- Diferenciación visual entre grupos mediante cajas

#### Cambios Implementados

**Modificaciones en app.py**:
1. Actualización de `get_vm_status()` para incluir los nuevos servidores
2. Actualización de `get_vm_alerts()` con datos para los nuevos servidores
3. Refactorización de `main_dashboard()` para mostrar dos grupos separados
4. Implementación de cajas visuales diferenciadas:
   - SAP ISU PRODUCCIÓN: Caja con borde azul (#1f77b4) y fondo azul claro
   - SAP ERP: Caja con borde naranja (#ff7f0e) y fondo naranja claro

**Características agregadas**:
- ✅ Segundo grupo SAP ERP con 2 servidores
- ✅ Cajas visuales para diferenciar grupos
- ✅ Colores distintivos por grupo
- ✅ Estados y alertas configurados para nuevos servidores

**Decisiones de diseño**:
- Uso de colores contrastantes pero armoniosos para diferenciar grupos
- Mantenimiento del layout de 3 columnas, dejando una vacía en el grupo SAP ERP
- Conservación del mismo estilo visual para los indicadores de estado

### 2025-09-10 - Tercera Iteración: Estilización y Diseño Moderno

#### Requerimientos del Usuario
El usuario solicitó estilizar la aplicación para hacerla más bonita e impactante visualmente.

#### Cambios Implementados

**Patrón de Diseño Aplicado**: Glassmorphism + Futuristic Dark Theme

**Principales mejoras visuales**:
1. **Tema Oscuro Futurista**
   - Fondo con gradiente oscuro (#0a0f1c a #1a1f2e)
   - Efecto glassmorphism con backdrop-filter blur
   - Transparencias y bordes sutiles

2. **Animaciones y Efectos**
   - Animación de pulso en indicadores de estado
   - Efectos hover en tarjetas (elevación y brillo)
   - Transiciones suaves con cubic-bezier
   - Sombras dinámicas con colores de acento

3. **Mejoras Tipográficas**
   - Fuente Inter de Google Fonts
   - Título principal con gradiente de texto
   - Jerarquía visual clara con tamaños y pesos

4. **Componentes Rediseñados**
   - Tarjetas de servidor con bordes gradiente al hover
   - Botones con gradientes y efectos de elevación
   - Progress bars con gradientes vibrantes
   - Indicadores de estado con brillos y sombras de neón

5. **Nuevas Características Visuales**
   - Footer con resumen global del sistema
   - Métricas de disponibilidad con indicadores delta
   - Iconos para mejor identificación visual
   - Colores vibrantes: cyan (#00d4ff), verde neón (#00ff88), morado (#667eea)

**Decisiones técnicas**:
- CSS personalizado extenso para control total del diseño
- Uso de gradientes lineales para elementos destacados
- Animaciones CSS puras para mejor rendimiento
- Diseño responsive mantenido con mejoras visuales