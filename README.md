# Dashboard EPMAPS POC

Dashboard de monitoreo centralizado para máquinas virtuales, diseñado para visualizar la salud de infraestructura crítica con capacidad de expansión para reportes y análisis de tendencias.

## Características Actuales

- 🚦 Visualización del estado de VMs en tiempo real desde AWS.
- 📊 Conteo de alarmas de CloudWatch por instancia (OK, Alarma, Datos Insuficientes).
- 📈 Métricas de CPU en vivo desde CloudWatch.
- ☁️ Arquitectura Multi-Usuario eficiente con caché compartido en background.
- 🐳 Soporte para despliegue en contenedores (Docker).
- 🚀 Estrategia de despliegue recomendada usando AWS App Runner.

---

## Despliegue y Ejecución

### Ejecución Local (para Desarrollo)

1.  **Clonar el repositorio**
    ```bash
    git clone [url-del-repo]
    cd [nombre-del-repo]
    ```
2.  **Instalar dependencias**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configurar credenciales de AWS**
    Asegúrate de tener tus credenciales de AWS configuradas localmente para que `boto3` pueda usarlas. La forma más común es con el comando `aws configure`.

4.  **Ejecutar la aplicación**
    ```bash
    streamlit run app.py
    ```

### Despliegue en AWS (Recomendado)

La estrategia recomendada para producción o una beta compartida es usar **AWS App Runner**, que es una solución serverless, económica y totalmente gestionada.

- **Consulta la guía de despliegue detallada aquí:** [`docs/deploy_using_app_runner.md`](docs/deploy_using_app_runner.md)

También existe una guía para el despliegue alternativo en una instancia EC2:
- **Guía para EC2:** [`docs/deploy_using_ec2instance.md`](docs/deploy_using_ec2instance.md)

---

## Estructura del Proyecto

```
POC/
├── app.py                    # Script principal (redirige a la página de Producción)
├── Dockerfile                # Receta para construir el contenedor de la aplicación
├── requirements.txt          # Dependencias de Python
├── config.yaml               # Configuración de grupos de servidores (para páginas mock)
├── assets/
│   └── styles.css           # Estilos CSS
├── docs/
│   ├── deploy_using_app_runner.md # Guía de despliegue con App Runner
│   └── deploy_using_ec2instance.md  # Guía de despliegue con EC2
├── pages/
│   ├── 1_Production.py       # Dashboard del ambiente de Producción (Mock)
│   ├── 2_QA.py               # Dashboard del ambiente de QA (Mock)
│   ├── 3_DEV.py              # Dashboard del ambiente de DEV (Mock)
│   ├── 4_POC.py              # Dashboard con datos reales de AWS
│   └── hidden/               # Subpáginas no visibles en el menú
│       ├── _1_Detalles_del_Servidor.py
│       └── _5_POC_Detalles.py
├── utils/
│   └── helpers.py           # Funciones auxiliares
└── DEVELOPMENT_HISTORY.md    # Histórico detallado de desarrollo
```

---

## Changelog Reciente

### [5.0.0] - 2025-09-10 (Beta 1)

#### Agregado
- **Soporte para Contenedores:** Se añadió un `Dockerfile` para empaquetar la aplicación, permitiendo despliegues modernos.
- **Guías de Despliegue:** Se crearon documentos detallados para desplegar la aplicación usando **AWS App Runner** (recomendado) y EC2.

#### Modificado
- **Refactorización a `boto3`:** Se eliminó por completo la dependencia de `aws-cli`. Todas las llamadas a AWS ahora se realizan de forma nativa en Python usando la librería `boto3`, lo que mejora la seguridad, el rendimiento y la portabilidad.
- **Navegación Mejorada:** Se corrigió la navegación a las páginas de detalle y se limpió la barra lateral para una mejor experiencia de usuario.
- **Página de Inicio:** La aplicación ahora carga directamente en la página de "Producción".

*(Para ver el historial completo, revisa el archivo `DEVELOPMENT_HISTORY.md`)*

---

## Requisitos

- Python 3.8+
- Streamlit, Plotly, PyYAML, Boto3
- Docker (para construcción de contenedores)
