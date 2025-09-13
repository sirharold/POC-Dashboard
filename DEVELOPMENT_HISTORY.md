# Histórico de Desarrollo - Dashboard EPMAPS POC

Este archivo documenta todas las instrucciones, cambios y evolución del proyecto para poder retomar el desarrollo en cualquier punto.

## Contexto del Proyecto

**Objetivo**: Crear una aplicación con Streamlit que viva dentro de AWS para monitoreo de salud de máquinas virtuales, con capacidad de expansión futura para reportes, tendencias, etc.

**Tecnologías**:
- Streamlit (framework principal)
- Boto3 (AWS SDK para Python)
- Docker (Contenedores)
- AWS App Runner / EC2 (Despliegue Serverless / Instancia)
- GitHub Actions (CI/CD)
- YAML (Configuración)

## Registro de Desarrollo

### 2025-09-12 - Continuous Deployment and Data Loading Fixes

#### Objective
Establish a robust CI/CD pipeline for deploying the Streamlit app to EC2 and resolve data loading issues.

#### Problems Encountered & Solutions
1.  **GitHub Actions Permission Denied (`fatal: failed to stat ... Permission Denied`)**:
    *   **Problem:** The `ssm-user` running the SSM command in GitHub Actions could not access the application directory (`APP_PATH`), and the `ec2-user` (intended owner) also lacked permissions.
    *   **Solution:** Modified `deploy.yml` to ensure the application directory (`/home/ec2-user/POC-Dashboard`) is created and owned by `ec2-user` *before* any `git` operations.
2.  **GitHub Actions `fatal: not a git repository`**:
    *   **Problem:** After fixing permissions, the `git pull` command failed because the newly created directory on EC2 was not a Git repository.
    *   **Solution:** Modified `deploy.yml` to include `git init` and `git remote add origin` before `git pull`, ensuring the directory is a proper Git repository.
3.  **GitHub Actions `remote origin already exists`**:
    *   **Problem:** On subsequent deployments, `git remote add origin` failed because the remote was already configured.
    *   **Solution:** Modified `deploy.yml` to conditionally add the remote origin, checking if it exists first.
4.  **Streamlit App "No se puede acceder a este sitio web"**:
    *   **Problem:** The Streamlit service was crashing on startup (`status=200/CHDIR`) because its `WorkingDirectory` in `/etc/systemd/system/streamlit.service` was pointing to the old path (`/home/ssm-user/POC-Dashboard/`).
    *   **Solution:** Updated the `streamlit.service` file on EC2 to set `WorkingDirectory=/home/ec2-user/POC-Dashboard`, reloaded `systemd` daemon, and restarted the service.
5.  **Streamlit App "Cargando datos desde AWS..." (Data Loading Issue)**:
    *   **Problem:** The application was stuck on the loading message, and logs showed `botocore.client.EC2` objects were not pickle-serializable, causing `st.cache_data` to fail in `get_cross_account_boto3_client()`.
    *   **Solution:** Changed `@st.cache_data` to `@st.cache_resource` for `get_cross_account_boto3_client()` in `app.py`, as recommended by Streamlit for non-serializable objects.
6.  **Lack of Real-time Data Refresh & Debugging Visibility**:
    *   **Problem:** The page was not auto-reloading, and debugging AWS data fetching issues was difficult without on-screen logs.
    *   **Solution:**
        *   Implemented a configurable auto-reload mechanism with a countdown timer in `app.py` (using `REFRESH_INTERVAL_SECONDS` from `config.yaml`).
        *   Added a `show_aws_errors` flag to `config.yaml` to control on-screen display of AWS errors.
        *   Enhanced `get_aws_data()` with more granular logging to `/tmp/streamlit_aws_debug.log`.
        *   Implemented a feature to display the content of `/tmp/streamlit_aws_debug.log` directly on the Streamlit page when `show_aws_errors` is enabled.

#### Files Modified:
*   `.github/workflows/deploy.yml`
*   `app.py`
*   `config.yaml`

### 2025-09-12 - Versión 6.1: Simplificación de Navegación - Solo POC AWS Alive

#### Resumen
Se simplificó la navegación de la aplicación para mostrar únicamente la página "POC AWS Alive" en el sidebar, ocultando todas las páginas auxiliares y de entornos de prueba (Production, QA, DEV). La aplicación ahora redirige automáticamente a POC AWS Alive al iniciar.

#### Cambios Implementados

1. **Redirección Automática en `app.py`**:
   * Se eliminó el sidebar manual con múltiples enlaces
   * Se implementó redirección automática a POC AWS Alive usando `st.switch_page()`
   * Se configuró `initial_sidebar_state="collapsed"` para ocultar el sidebar por defecto

2. **Renombrado de Página Principal**:
   * `pages/4_POC.py` → `pages/POC_AWS_Alive.py`
   * Esto elimina el prefijo numérico y mejora la claridad del nombre

3. **Actualización de Referencias de Navegación**:
   * Se actualizaron todas las referencias en `_5_POC_Detalles.py` para apuntar a `POC_AWS_Alive.py`
   * Las páginas con prefijo `_` permanecen ocultas del sidebar como es esperado

#### Justificación
El usuario reportó que las páginas con prefijo `_` seguían apareciendo en el sidebar debido al uso de navegación manual con `st.sidebar.page_link()`. Al eliminar esta navegación manual y usar el comportamiento automático de Streamlit, solo las páginas sin prefijo `_` son visibles, logrando el objetivo de mostrar únicamente POC AWS Alive.

### 2025-09-12 - Versión 6.0 (Beta 2): Refactorización Arquitectónica y Despliegue Automatizado

#### Resumen
Esta versión representa la refactorización más grande hasta la fecha. La aplicación monolítica (`app.py`) fue desmantelada y reconstruida sobre una arquitectura modular, escalable y configurable, alineada con las mejores prácticas de desarrollo de software. Además, se implementó un flujo de despliegue continuo (CI/CD).

#### Cambios Implementados

1.  **Arquitectura Multi-Página y Componentizada**:
    *   La aplicación se transformó en una **aplicación multi-página**, con archivos dedicados para cada entorno (`Producción`, `QA`, `DEV`) en el directorio `pages/`.
    *   Se crearon **componentes de UI reutilizables** (`server_card.py`, `group_container.py`) para encapsular la lógica de renderizado y promover la reutilización de código.
    *   La lógica común y funciones de ayuda se centralizaron en `utils/helpers.py`.

2.  **Configuración Externa con `config.yaml`**:
    *   Toda la definición de servidores, grupos y estados se movió a un archivo `config.yaml`.
    *   **Beneficio:** Ahora es posible añadir, modificar o eliminar servidores y grupos sin necesidad de editar el código Python, facilitando enormemente el mantenimiento.

3.  **Mejoras de Navegación y Experiencia de Usuario**:
    *   `app.py` ahora funciona como un **portal de bienvenida** que construye una barra de navegación lateral personalizada, ofreciendo una experiencia más limpia.
    *   Se añadió un **navegador entre entornos** (flechas ᐊ y ᐅ) en las páginas principales.
    *   La navegación a las páginas de detalle fue refactorizada para usar **parámetros de consulta en la URL** (`st.query_params`), un método más robusto y estándar que `st.session_state`.

4.  **Optimización de la Página POC (AWS Live)**:
    *   La página `4_POC.py` fue rediseñada para usar un **sistema de cache en memoria compartida**.
    *   Un **hilo de fondo (background thread)** se encarga de actualizar los datos desde AWS (`boto3`) cada 30 segundos.
    *   **Beneficio:** Todos los usuarios concurrentes acceden a la misma cache, lo que reduce drásticamente las llamadas a la API de AWS, mejora el rendimiento y la escalabilidad de la aplicación.

5.  **Despliegue Continuo con GitHub Actions**:
    *   Se creó el flujo de trabajo `.github/workflows/deploy.yml`.
    *   Este flujo **automatiza el despliegue** de la aplicación en la instancia EC2 designada cada vez que se realiza un `push` a la rama `main`.
    *   Utiliza `AWS SSM Send-Command` para ejecutar los comandos de actualización en la instancia de forma segura.

#### Decisión de Arquitectura
Se adoptó una arquitectura modular y basada en configuración para preparar la aplicación para un crecimiento futuro. La separación de la configuración (`config.yaml`), la lógica (`utils/`), los componentes de UI (`components/`) y las vistas (`pages/`) hace que el sistema sea más fácil de entender, mantener y escalar. La implementación de CI/CD con GitHub Actions profesionaliza el ciclo de vida del desarrollo.

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

## Estructura del Proyecto (v6.0)

```
POC/
├── .github/                    # Flujos de trabajo de CI/CD
│   └── workflows/
│       └── deploy.yml
├── app.py                      # Página principal y navegador
├── config.yaml                 # Configuración de servidores y grupos
├── Dockerfile                  # Contenerización de la aplicación
├── requirements.txt            # Dependencias de Python
├── assets/
│   └── styles.css              # Hoja de estilos CSS
├── components/
│   ├── group_container.py      # Componente para grupos de servidores
│   └── server_card.py          # Componente para tarjetas de servidor
├── docs/
│   ├── deploy_using_app_runner.md
│   └── deploy_using_ec2instance.md
├── pages/
│   ├── 1_Production.py         # Página para el entorno de Producción (oculta del menú)
│   ├── 2_QA.py                 # Página para el entorno de QA (oculta del menú)
│   ├── 3_DEV.py                # Página para el entorno de DEV (oculta del menú)
│   ├── POC_AWS_Alive.py        # Página principal con datos reales de AWS (única visible)
│   ├── _1_Detalles_del_Servidor.py # Página de detalle (oculta)
│   ├── _5_POC_Detalles.py      # Página de detalles POC (oculta)
│   └── _vm_details.py          # Página de detalles VM (oculta)
├── utils/
│   └── helpers.py              # Funciones de ayuda y lógica compartida
├── DEVELOPMENT_HISTORY.md      # Este archivo
└── README.md                   # Documentación principal
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