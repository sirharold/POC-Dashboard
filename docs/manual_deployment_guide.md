# Guía de Despliegue Manual en AWS Fargate (Consola)

Esta guía proporciona instrucciones paso a paso para desplegar la aplicación Streamlit en AWS Fargate utilizando la consola de AWS, aprovechando los recursos que ya deberían haber sido creados por el script `deploy_fargate.sh` (incluso si falló en la creación del servicio ECS).

## Prerrequisitos

*   Acceso a la Consola de AWS con las credenciales adecuadas.
*   La imagen Docker de la aplicación debe estar disponible en Amazon ECR.
    *   **URI de la Imagen ECR:** `687634808667.dkr.ecr.us-east-1.amazonaws.com/dashboard-epmaps-poc@sha256:63d8382fa2142442370a48c0704dfc19fc09d71407b9775fdb84be07ec640d78`
*   Los siguientes recursos ya deberían existir (creados por el script `deploy_fargate.sh`):
    *   **Roles de IAM:** `ecsTaskExecutionRole`, `streamlit-task-role`
    *   **Security Groups:** `streamlit-alb-sg`, `streamlit-dashboard-service-sg`
    *   **VPC ID:** `vpc-029a13c34d0d033f0`
    *   **Subnets:** `subnet-0ee2c29fb5619f792`, `subnet-0bdffbaa0174a9736`
    *   **ALB (Application Load Balancer):** `streamlit-alb`
    *   **Target Group:** `streamlit-tg`
    *   **Cluster ECS:** `streamlit-dashboard-cluster`

## Pasos para el Despliegue Manual

### 0. Verificar Prerrequisitos Existentes (Opcional, pero Recomendado)

Antes de iniciar el despliegue manual, puedes verificar que los recursos necesarios (creados por `deploy_fargate.sh`) existen y están en un estado válido. Si alguno de estos comandos falla, significa que el recurso no se creó correctamente y deberías revisar la ejecución del script `deploy_fargate.sh` o crearlo manualmente.

*   **Verificar Roles de IAM:**
    ```bash
    aws iam get-role --role-name ecsTaskExecutionRole --region us-east-1
    aws iam get-role --role-name streamlit-task-role --region us-east-1
    ```
*   **Verificar Security Groups:**
    ```bash
    aws ec2 describe-security-groups --group-names streamlit-alb-sg --region us-east-1
    aws ec2 describe-security-groups --group-names streamlit-dashboard-service-sg --region us-east-1
    ```
*   **Verificar ALB y Target Group:**
    ```bash
    aws elbv2 describe-load-balancers --names streamlit-alb --region us-east-1
    aws elbv2 describe-target-groups --names streamlit-tg --region us-east-1
    ```
*   **Verificar Cluster ECS:**
    ```bash
    aws ecs describe-clusters --cluster-name streamlit-dashboard-cluster --query "clusters[0].clusterArn" --output text --region us-east-1
    ```
    Si este comando no devuelve nada o un error, el cluster no existe. Deberás crearlo manualmente o asegurarte de que el script `deploy_fargate.sh` lo haya creado.

### 1. Crear Definición de Tarea (Task Definition)

1.  Navega a la consola de AWS y busca **ECS (Elastic Container Service)**.
2.  En el panel de navegación izquierdo, selecciona **"Task Definitions"** y luego haz clic en **"Create new task definition"**.
3.  Selecciona **"Fargate"** como tipo de lanzamiento y haz clic en **"Next step"**.
4.  **Configurar Definición de Tarea:**
    *   **Task Definition Name:** `streamlit-dashboard-task`
    *   **Task Role:** Selecciona `streamlit-task-role` (¡Crucial! Este rol le da permisos a tu aplicación).
    *   **Task execution role:** Selecciona `ecsTaskExecutionRole` (¡Crucial! Este rol le da permisos a ECS para ejecutar la tarea).
    *   **Compatible with:** Fargate
    *   **Task memory (GB):** `4 GB` (4096 MB)
    *   **Task CPU (vCPU):** `2 vCPU` (2048 unidades)
5.  **Añadir Contenedor (Container Definition):**
    *   Haz clic en **"Add container"**.
    *   **Container name:** `streamlit-app`
    *   **Image:** Pega la URI de la imagen ECR: `687634808667.dkr.ecr.us-east-1.amazonaws.com/dashboard-epmaps-poc@sha256:63d8382fa2142442370a48c0704dfc19fc09d71407b9775fdb84be07ec640d78`
    *   **Port mappings:**
        *   **Host port:** `8501`
        *   **Container port:** `8501`
        *   **Protocol:** `tcp`
    *   **Environment variables:** Añade las siguientes variables de entorno (tipo `KEY-VALUE`):
        *   `STREAMLIT_SERVER_PORT`: `8501`
        *   `STREAMLIT_SERVER_ADDRESS`: `0.0.0.0`
        *   `STREAMLIT_SERVER_ENABLE_CORS`: `false`
        *   `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION`: `false`
        *   `STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION`: `false`
    *   **Log configuration:**
        *   **Log driver:** `awslogs`
        *   **Options:**
            *   `awslogs-group`: `/ecs/streamlit-dashboard-task`
            *   `awslogs-region`: `us-east-1`
            *   `awslogs-stream-prefix`: `ecs`
    *   Haz clic en **"Add"** y luego en **"Create"** para la definición de tarea.

### 2. Crear Servicio (Service) de ECS

1.  En el panel de navegación izquierdo de ECS, selecciona **"Clusters"** y haz clic en el cluster `streamlit-dashboard-cluster`.
2.  En la pestaña **"Services"**, haz clic en **"Create"**.
3.  **Configurar Servicio:**
    *   **Launch type:** `Fargate`
    *   **Task Definition:** Selecciona la definición de tarea que acabas de crear (`streamlit-dashboard-task`).
    *   **Cluster:** `streamlit-dashboard-cluster`
    *   **Service name:** `streamlit-dashboard-service`
    *   **Number of desired tasks:** `1`
4.  **Configuración de Red (Networking):**
    *   **VPC:** Selecciona `vpc-029a13c34d0d033f0`.
    *   **Subnets:** Selecciona las subredes `subnet-0ee2c29fb5619f792` y `subnet-0bdffbaa0174a9736`.
    *   **Security groups:** Selecciona el Security Group `streamlit-dashboard-service-sg`.
    *   **Public IP:** Asegúrate de que **"ENABLED"** esté seleccionado para `Auto-assign Public IP`.
5.  **Balanceo de Carga (Load Balancing):**
    *   **Load balancer type:** Selecciona `Application Load Balancer`.
    *   **Load balancer name:** Selecciona `streamlit-alb`.
    *   **Container to load balance:** Haz clic en **"Add to load balancer"**.
        *   **Container name: port:** `streamlit-app:8501`
        *   **Target group name:** Selecciona `streamlit-tg`.
6.  Revisa el resto de las configuraciones (Auto Scaling, etc.) y haz clic en **"Next step"** hasta llegar a **"Create Service"**.

### 3. Verificar Despliegue

1.  Una vez creado el servicio, ve a la pestaña **"Tasks"** dentro de tu servicio ECS. Deberías ver una tarea en estado `RUNNING`.
2.  Navega a la consola de **EC2** y busca **"Load Balancers"**. Selecciona `streamlit-alb` y copia su **DNS name**.
3.  Pega el DNS name en tu navegador. Deberías ver la aplicación Streamlit.

### 4. Acceso a la Aplicación (Vía CloudFront)

Si ya tienes una distribución de CloudFront configurada para apuntar a tu ALB, puedes acceder a la aplicación a través del dominio de CloudFront. Si no, puedes seguir la guía `cloudfront_deployment.md` para configurarla.

---
