# Dashboard EPMAPS POC

Dashboard de monitoreo centralizado para máquinas virtuales, diseñado para visualizar la salud de infraestructura crítica con capacidad de expansión para reportes y análisis de tendencias.

## Características Actuales

- 🏛️ **Arquitectura Multi-Página**: Navegación dedicada para cada entorno (PROD, QA, DEV).
- ⚙️ **Configuración Externa**: Los servidores y grupos se gestionan desde `config.yaml`, sin tocar el código.
- 🧩 **Componentes Reutilizables**: UI modular que facilita el mantenimiento y la expansión.
- ☁️ **Integración Real con AWS**: Una página POC se conecta en tiempo real a AWS usando `boto3`.
- ⚡ **Cache Inteligente**: La página de AWS utiliza un hilo de fondo y una cache compartida para un rendimiento óptimo y multiusuario.
- 🚀 **Despliegue Continuo (CI/CD)**: Automatización del despliegue a EC2 mediante **GitHub Actions** cada vez que se actualiza la rama `main`.
- 🐳 **Soporte para Contenedores**: `Dockerfile` incluido para despliegues portables.

---

## Despliegue y Ejecución

### Ejecución Local (para Desarrollo)

1.  **Clonar el repositorio**
2.  **Instalar dependencias**: `pip install -r requirements.txt`
3.  **Configurar credenciales de AWS** (si se va a usar la página POC Live).
4.  **Ejecutar la aplicación**: `streamlit run app.py`

### Despliegue en AWS

Existen dos métodos de despliegue documentados:

1.  **AWS App Runner (Recomendado)**: Serverless, económico y gestionado.
    - **Guía:** [`docs/deploy_using_app_runner.md`](docs/deploy_using_app_runner.md)
2.  **Instancia EC2 con CI/CD (Configuración Actual)**: Despliegue automatizado desde GitHub.
    - **Guía:** [`docs/deploy_using_ec2instance.md`](docs/deploy_using_ec2instance.md)

---

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
│   ├── 1_Production.py         # Página para el entorno de Producción
│   ├── 2_QA.py                 # Página para el entorno de QA
│   ├── 3_DEV.py                # Página para el entorno de DEV
│   ├── 4_POC.py                # Página con datos reales de AWS
│   └── _1_Detalles_del_Servidor.py # Página de detalle (oculta)
├── utils/
│   └── helpers.py              # Funciones de ayuda y lógica compartida
├── DEVELOPMENT_HISTORY.md      # Histórico detallado de cambios
└── README.md                   # Este archivo
```

---

## Changelog Reciente

### [6.0.0] - 2025-09-12 (Beta 2)

#### Agregado
- **Arquitectura Modular**: La aplicación fue refactorizada a un modelo multi-página con componentes reutilizables (`components/`) y lógica centralizada (`utils/`).
- **Configuración Externa**: Se añadió `config.yaml` para gestionar servidores y grupos fuera del código.
- **Despliegue Automatizado**: Se implementó un flujo de CI/CD con GitHub Actions para actualizar la instancia EC2 automáticamente.
- **Cache Inteligente en POC**: La página de AWS ahora usa un hilo de fondo para actualizar una cache compartida, mejorando el rendimiento.

#### Modificado
- **Navegación**: `app.py` ahora es un portal de bienvenida. La navegación a detalles usa `st.query_params`.

### [5.0.0] - 2025-09-10 (Beta 1)

#### Agregado
- **Soporte para Contenedores:** Se añadió un `Dockerfile`.
- **Guías de Despliegue:** Se crearon documentos para AWS App Runner y EC2.

#### Modificado
- **Refactorización a `boto3`:** Se eliminó la dependencia de `aws-cli`.

*(Para ver el historial completo, revisa el archivo `DEVELOPMENT_HISTORY.md`)*

---

## Requisitos

- Python 3.8+
- Streamlit, Plotly, PyYAML, Boto3
- Docker (para construcción de contenedores)