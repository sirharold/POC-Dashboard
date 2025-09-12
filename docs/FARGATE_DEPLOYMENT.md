# Despliegue de Aplicación Streamlit en AWS Fargate

Este documento detalla los pasos para desplegar una aplicación Streamlit en AWS Fargate, cubriendo el proceso manual (para aprendizaje) y una visión general del proceso automatizado. Se asume que ya tienes una VPC con subredes públicas configuradas.

---

## 1. Despliegue Manual (Paso a Paso)

Este proceso te guiará a través de la consola de AWS y la AWS CLI para configurar tu aplicación Streamlit en Fargate.

### Prerrequisitos

Antes de comenzar, asegúrate de tener lo siguiente:

*   **Imagen Docker en ECR:** Tu imagen de la aplicación Streamlit (`dashboard-epmaps-poc:latest`) debe estar ya construida y subida a Amazon Elastic Container Registry (ECR). (Ya completamos esto en los pasos anteriores).
*   **AWS CLI:** La Interfaz de Línea de Comandos de AWS debe estar instalada y configurada con las credenciales adecuadas.
*   **Docker:** Docker Desktop debe estar instalado y en ejecución en tu máquina local.
*   **VPC y Subredes Públicas:** Debes tener una Virtual Private Cloud (VPC) con al menos dos subredes públicas en diferentes Zonas de Disponibilidad en la región `us-east-1`.

---

### Paso 1: Crear Roles de IAM

Necesitarás dos roles de IAM para que Fargate funcione correctamente:

1.  **ecsTaskExecutionRole:** Permite que el agente de contenedor de ECS realice llamadas a la API de AWS en tu nombre (ej. pull de imágenes de ECR, push de logs a CloudWatch).
2.  **ecsTaskRole (Opcional):** Si tu aplicación Streamlit necesita acceder a otros servicios de AWS (ej. S3, DynamoDB, u otros servicios de AWS como boto3), necesitarás un rol de tarea. Para este caso, como tu aplicación usa `boto3`, lo crearemos.

**Opción A: Usando la AWS CLI**

1.  **Crear `ecsTaskExecutionRole`:**

    Crea un archivo `ecs-tasks-trust-policy.json`:
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "ecs-tasks.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    ```
    Crea el rol:
    ```bash
    aws iam create-role \
        --role-name ecsTaskExecutionRole \
        --assume-role-policy-document file://ecs-tasks-trust-policy.json \
        --region us-east-1
    ```
    Adjunta la política gestionada:
    ```bash
    aws iam attach-role-policy \
        --role-name ecsTaskExecutionRole \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
        --region us-east-1
    ```

2.  **Crear `streamlit-task-role` (Rol de Tarea para tu aplicación):**

    Crea un archivo `streamlit-task-trust-policy.json` (similar al anterior):
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "ecs-tasks.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    ```
    Crea el rol:
    ```bash
    aws iam create-role \
        --role-name streamlit-task-role \
        --assume-role-policy-document file://streamlit-task-trust-policy.json \
        --region us-east-1
    ```
    Adjunta las políticas necesarias para tu aplicación (ej. `AmazonS3ReadOnlyAccess` si lee de S3, o políticas específicas para `boto3`). Para este ejemplo, asumiremos que necesita acceso de solo lectura a S3 y CloudWatch para logs:
    ```bash
    aws iam attach-role-policy \
        --role-name streamlit-task-role \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
        --region us-east-1

    aws iam attach-role-policy \
        --role-name streamlit-task-role \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess \
        --region us-east-1
    ```

**Opción B: Usando la Consola de AWS**

1.  Navega a la consola de **IAM**.
2.  En el panel de navegación izquierdo, haz clic en **"Roles"**.
3.  Haz clic en **"Create role"**.
4.  **Para `ecsTaskExecutionRole`:**
    *   **Trusted entity type:** `AWS service`
    *   **Use case:** `Elastic Container Service` -> `ECS Task`
    *   Haz clic en **"Next"**.
    *   **Permissions policies:** Busca y selecciona `AmazonECSTaskExecutionRolePolicy`.
    *   Haz clic en **"Next"**.
    *   **Role name:** `ecsTaskExecutionRole`
    *   Haz clic en **"Create role"**.

5.  **Para `streamlit-task-role`:**
    *   **Trusted entity type:** `AWS service`
    *   **Use case:** `Elastic Container Service` -> `ECS Task`
    *   Haz clic en **"Next"**.
    *   **Permissions policies:** Busca y selecciona las políticas que tu aplicación necesita (ej. `AmazonS3ReadOnlyAccess`, `CloudWatchReadOnlyAccess`).
    *   Haz clic en **"Next"**.
    *   **Role name:** `streamlit-task-role`
    *   Haz clic en **"Create role"**.

---

### Paso 2: Configurar Grupos de Seguridad

Los grupos de seguridad actúan como firewalls virtuales. Necesitarás dos:

1.  **Grupo de Seguridad para el ALB (streamlit-alb-sg):** Permite el tráfico HTTP/HTTPS desde Internet.
2.  **Grupo de Seguridad para las Tareas de Fargate (streamlit-fargate-sg):** Permite el tráfico entrante desde el ALB en el puerto de tu aplicación (8501).

**Opción A: Usando la AWS CLI**

1.  **Crear Grupo de Seguridad para el ALB:**

    ```bash
    aws ec2 create-security-group \
        --group-name streamlit-alb-sg \
        --description "Security group for Streamlit ALB" \
        --vpc-id vpc-YOUR_VPC_ID \
        --region us-east-1
    ```
    *   Reemplaza `vpc-YOUR_VPC_ID` con el ID de tu VPC.
    *   Toma nota del `GroupId` que devuelve este comando.

2.  **Añadir reglas de entrada al ALB SG (HTTP y HTTPS):**

    ```bash
    aws ec2 authorize-security-group-ingress \
        --group-id sg-ALB-SECURITY-GROUP-ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region us-east-1

    aws ec2 authorize-security-group-ingress \
        --group-id sg-ALB-SECURITY-GROUP-ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region us-east-1
    ```
    *   Reemplaza `sg-ALB-SECURITY-GROUP-ID` con el ID del grupo de seguridad que acabas de crear.

3.  **Crear Grupo de Seguridad para las Tareas de Fargate:**

    ```bash
    aws ec2 create-security-group \
        --group-name streamlit-fargate-sg \
        --description "Security group for Streamlit Fargate tasks" \
        --vpc-id vpc-YOUR_VPC_ID \
        --region us-east-1
    ```
    *   Reemplaza `vpc-YOUR_VPC_ID` con el ID de tu VPC.
    *   Toma nota del `GroupId` que devuelve este comando.

4.  **Añadir regla de entrada al Fargate SG (desde el ALB):**

    ```bash
    aws ec2 authorize-security-group-ingress \
        --group-id sg-FARGATE-SECURITY-GROUP-ID \
        --protocol tcp \
        --port 8501 \
        --source-group sg-ALB-SECURITY-GROUP-ID \
        --region us-east-1
    ```
    *   Reemplaza `sg-FARGATE-SECURITY-GROUP-ID` con el ID del grupo de seguridad de Fargate.
    *   Reemplaza `sg-ALB-SECURITY-GROUP-ID` con el ID del grupo de seguridad del ALB.

**Opción B: Usando la Consola de AWS**

1.  Navega a la consola de **Amazon EC2**.
2.  En el panel de navegación izquierdo, bajo **"Network & Security"**, haz clic en **"Security Groups"**.
3.  **Crear Grupo de Seguridad para el ALB (streamlit-alb-sg):**
    *   Haz clic en **"Create security group"**.
    *   **Security group name:** `streamlit-alb-sg`
    *   **Description:** `Security group for Streamlit ALB`
    *   **VPC:** Selecciona tu VPC.
    *   **Inbound rules:**
        *   **Type:** `HTTP`, **Source:** `Anywhere-IPv4`
        *   **Type:** `HTTPS`, **Source:** `Anywhere-IPv4` (si planeas usar HTTPS)
    *   Haz clic en **"Create security group"**.
4.  **Crear Grupo de Seguridad para las Tareas de Fargate (streamlit-fargate-sg):**
    *   Haz clic en **"Create security group"**.
    *   **Security group name:** `streamlit-fargate-sg`
    *   **Description:** `Security group for Streamlit Fargate tasks`
    *   **VPC:** Selecciona tu VPC.
    *   **Inbound rules:**
        *   **Type:** `Custom TCP`, **Port range:** `8501`, **Source:** Selecciona el grupo de seguridad `streamlit-alb-sg` que acabas de crear.
    *   Haz clic en **"Create security group"**.

**Importante:** Una vez creados, asegúrate de asociar estos grupos de seguridad a tus recursos:
*   El `streamlit-alb-sg` debe estar asociado a tu **Application Load Balancer**.
*   El `streamlit-fargate-sg` debe estar asociado a las **tareas de Fargate** (esto se hace al configurar el servicio ECS).

---

### Paso 3: Crear un Balanceador de Carga (ALB) y Grupo Objetivo

Un Application Load Balancer (ALB) distribuirá el tráfico entrante a tus tareas de Fargate y manejará las conexiones HTTP/HTTPS.

**Opción A: Usando la AWS CLI**

Este es un proceso de varios pasos en la CLI. Primero, crea el ALB, luego un Target Group, y finalmente un Listener.

1.  **Crear el ALB:**

    ```bash
    aws elbv2 create-load-balancer \
        --name streamlit-alb \
        --subnets subnet-XXXXXXXXXXXXXXX subnet-YYYYYYYYYYYYYYY \
        --security-groups sg-ALB-SECURITY-GROUP-ID \
        --scheme internet-facing \
        --type application \
        --region us-east-1
    ```
    *   Reemplaza `subnet-XXXXXXXXXXXXXXX` y `subnet-YYYYYYYYYYYYYYY` con los IDs de tus subredes públicas.
    *   Reemplaza `sg-ALB-SECURITY-GROUP-ID` con el ID del grupo de seguridad del ALB que creaste en el Paso 2.

2.  **Crear un Target Group:**

    ```bash
    aws elbv2 create-target-group \
        --name streamlit-tg \
        --protocol HTTP \
        --port 8501 \
        --vpc-id vpc-YOUR_VPC_ID \
        --target-type ip \
        --health-check-protocol HTTP \
        --health-check-path / \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 2 \
        --region us-east-1
    ```
    *   Reemplaza `vpc-YOUR_VPC_ID` con el ID de tu VPC.

3.  **Crear un Listener para el ALB:**

    ```bash
    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:YOUR_AWS_ACCOUNT_ID:loadbalancer/app/streamlit-alb/xxxxxxxxxxxxxx \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:YOUR_AWS_ACCOUNT_ID:targetgroup/streamlit-tg/xxxxxxxxxxxxxx \
        --region us-east-1
    ```
    *   Reemplaza los ARNs del Load Balancer y del Target Group con los que obtuviste de los comandos anteriores.
    *   Reemplaza `YOUR_AWS_ACCOUNT_ID` con tu ID de cuenta de AWS.

**Opción B: Usando la Consola de AWS**

1.  Navega a la consola de **Amazon EC2**.
2.  En el panel de navegación izquierdo, bajo **"Load Balancing"**, haz clic en **"Load Balancers"**.
3.  Haz clic en **"Create Load Balancer"**.
4.  Selecciona **"Application Load Balancer"** y haz clic en **"Create"**.
5.  **Configura el ALB:**
    *   **Load balancer name:** `streamlit-alb`
    *   **Scheme:** `Internet-facing`
    *   **IP address type:** `IPv4`
    *   **VPC:** Selecciona tu VPC.
    *   **Mappings:** Selecciona al menos dos subredes públicas.
    *   **Security groups:** Selecciona el grupo de seguridad `streamlit-alb-sg` que creaste en el Paso 2.
6.  **Configura el Listener y el Target Group:**
    *   **Listeners:** `HTTP:80`
    *   **Default action:** Haz clic en **"Create target group"**.
        *   **Choose a target group type:** `IP addresses`
        *   **Target group name:** `streamlit-tg`
        *   **Protocol:** `HTTP`
        *   **Port:** `8501` (el puerto de tu aplicación Streamlit)
        *   **VPC:** Selecciona tu VPC.
        *   **Health checks:** `HTTP` en `/` (ruta raíz).
        *   Haz clic en **"Create target group"**.
    *   Vuelve a la pantalla de creación del ALB y selecciona el `streamlit-tg` que acabas de crear como **"Forward to"**.
7.  Haz clic en **"Create load balancer"**.

---

### Paso 4: Crear un Cluster de ECS

Un cluster de ECS es una agrupación lógica para tus tareas de Fargate. No pagas por el cluster en sí; solo pagas por los recursos que consumen tus tareas.

**Opción A: Usando la AWS CLI**

```bash
aws ecs create-cluster --cluster-name streamlit-dashboard-cluster --region us-east-1
```

**Opción B: Usando la Consola de AWS**

1.  Navega a la consola de **Amazon ECS**.
2.  En el panel de navegación izquierdo, haz clic en **"Clusters"**.
3.  Haz clic en **"Create Cluster"**.
4.  Selecciona el tipo de plantilla **"Networking only"** (para Fargate).
5.  Asigna un **"Cluster name"**, por ejemplo: `streamlit-dashboard-cluster`.
6.  Haz clic en **"Create"**.

---

### Paso 5: Crear una Definición de Tarea de ECS

La definición de tarea es como un plano para tu aplicación. Especifica la imagen de Docker a usar, los recursos (CPU y memoria), los puertos, etc.

**Opción A: Usando la AWS CLI**

Primero, crea un archivo JSON para tu definición de tarea. Por ejemplo, `task-definition.json` en la raíz de tu proyecto:

```json
{
    "family": "streamlit-dashboard-task",
    "networkMode": "awsvpc",
    "cpu": "1024",
    "memory": "2048",
    "executionRoleArn": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/streamlit-task-role",
    "requiresCompatibilities": [
        "FARGATE"
    ],
    "containerDefinitions": [
        {
            "name": "streamlit-app",
            "image": "YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dashboard-epmaps-poc:latest",
            "portMappings": [
                {
                    "containerPort": 8501,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "environment": [
                {
                    "name": "STREAMLIT_SERVER_PORT",
                    "value": "8501"
                },
                {
                    "name": "STREAMLIT_SERVER_ADDRESS",
                    "value": "0.0.0.0"
                },
                {
                    "name": "STREAMLIT_SERVER_ENABLE_CORS",
                    "value": "false"
                },
                {
                    "name": "STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION",
                    "value": "false"
                },
                {
                    "name": "STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION",
                    "value": "false"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/streamlit-dashboard-task",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
```

**Importante:**
*   Reemplaza `YOUR_AWS_ACCOUNT_ID` con tu ID de cuenta de AWS.
*   `cpu` y `memory` están en unidades. `1024` CPU = 1 vCPU, `2048` memory = 2 GB. Para 2 vCPU y 4 GB, usarías `2048` para `cpu` y `4096` para `memory`. Ajusta según tus necesidades.
*   Asegúrate de que los roles `ecsTaskExecutionRole` y `streamlit-task-role` (si lo usas) existan y tengan los permisos correctos.

Luego, registra la definición de tarea con la CLI:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json --region us-east-1
```

**Opción B: Usando la Consola de AWS**

1.  Navega a la consola de **Amazon ECS**.

2.  En el panel de navegación izquierdo, haz clic en **"Task Definitions"**.

3.  Haz clic en **"Create new Task Definition"**.

4.  Selecciona **"Fargate"** como tipo de lanzamiento y haz clic en **"Next step"**.

5.  **Configura la definición de tarea:**
    *   **Task Definition Name:** `streamlit-dashboard-task`
    *   **Task Role:** Selecciona `streamlit-task-role` (si lo creaste).
    *   **Task Execution Role:** Selecciona `ecsTaskExecutionRole`.
    *   **Task memory (GB):** `4` (o el que desees)
    *   **Task CPU (vCPU):** `2` (o el que desees)
6.  **Configura el contenedor:**
    *   Haz clic en **"Add container"**.

    *   **Container name:** `streamlit-app`
    *   **Image:** `YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dashboard-epmaps-poc:latest` (reemplaza `YOUR_AWS_ACCOUNT_ID`)
    *   **Port mappings:** `8501` (para `container port`, deja `host port` en blanco)
    *   **Environment variables:** Añade las siguientes variables de entorno (tipo `KEY-VALUE`):
        *   `STREAMLIT_SERVER_PORT` : `8501`
        *   `STREAMLIT_SERVER_ADDRESS` : `0.0.0.0`
        *   `STREAMLIT_SERVER_ENABLE_CORS` : `false`
        *   `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION` : `false`
        *   `STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION` : `false`
    *   **Log configuration:**
        *   **Log driver:** `awslogs`
        *   **awslogs-group:** `/ecs/streamlit-dashboard-task` (crea este grupo de logs en CloudWatch si no existe)
        *   **awslogs-region:** `us-east-1`
        *   **awslogs-stream-prefix:** `ecs`
    *   Haz clic en **"Add"**.

7.  Haz clic en **"Create"** para registrar la definición de tarea.

---

### Paso 6: Crear un Servicio de ECS

El servicio de ECS se encarga de mantener el número deseado de tareas ejecutándose, manejar el balanceo de carga y el escalado automático.

**Opción A: Usando la AWS CLI**

```bash
aws ecs create-service \
    --cluster streamlit-dashboard-cluster \
    --service-name streamlit-dashboard-service \
    --task-definition streamlit-dashboard-task \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-XXXXXXXXXXXXXXX,subnet-YYYYYYYYYYYYYYY],securityGroups=[sg-FARGATE-SECURITY-GROUP-ID],assignPublicIp=ENABLED}" \
    --load-balancers "[{"targetGroupArn":"arn:aws:elasticloadbalancing:us-east-1:YOUR_AWS_ACCOUNT_ID:targetgroup/streamlit-tg/xxxxxxxxxxxxxx","containerName":"streamlit-app","containerPort":8501}]" \
    --region us-east-1
```

**Importante:**
*   Reemplaza `subnet-XXXXXXXXXXXXXXX`, `subnet-YYYYYYYYYYYYYYY` con los IDs de tus subredes públicas en tu VPC.
*   Reemplaza `sg-FARGATE-SECURITY-GROUP-ID` con el ID de tu grupo de seguridad para las tareas de Fargate que creaste en el Paso 2.
*   Reemplaza `arn:aws:elasticloadbalancing:us-east-1:YOUR_AWS_ACCOUNT_ID:targetgroup/streamlit-tg/xxxxxxxxxxxxxx` con el ARN de tu Target Group que creaste en el Paso 3.
*   Reemplaza `YOUR_AWS_ACCOUNT_ID` con tu ID de cuenta de AWS.

**Opción B: Usando la Consola de AWS**

1.  Navega a la consola de **Amazon ECS**.
2.  En el panel de navegación izquierdo, haz clic en **"Clusters"** y selecciona tu cluster `streamlit-dashboard-cluster`.
3.  Haz clic en la pestaña **"Services"** y luego en **"Create"**.
4.  **Configura el servicio:**
    *   **Launch type:** `Fargate`
    *   **Task Definition:** Selecciona `streamlit-dashboard-task` (la que creaste en el Paso 5).
    *   **Cluster:** `streamlit-dashboard-cluster`
    *   **Service name:** `streamlit-dashboard-service`
    *   **Desired tasks:** `1` (puedes ajustarlo más tarde para escalado automático).
    *   **Minimum healthy percent:** `100`
    *   **Maximum percent:** `200`
5.  **Configuración de red:**
    *   **VPC:** Selecciona tu VPC.
    *   **Subnets:** Selecciona al menos dos subredes públicas.
    *   **Security groups:** Selecciona el grupo de seguridad `streamlit-fargate-sg` que creaste en el Paso 2.
    *   **Public IP:** `ENABLED` (para que las tareas puedan acceder a Internet y ser accesibles desde el ALB).
6.  **Balanceo de carga (Load balancing):**
    *   Selecciona **"Application Load Balancer"**.
    *   **Load balancer name:** Selecciona el ALB `streamlit-alb` que creaste en el Paso 3.
    *   **Container to load balance:** Selecciona `streamlit-app:8501`.
    *   Haz clic en **"Add to load balancer"**.
    *   **Production listener port:** `80` (o `443` si usas HTTPS).
    *   **Target group name:** Selecciona el Target Group `streamlit-tg` que creaste en el Paso 3.
7.  **Auto Scaling (Opcional pero recomendado):**
    *   Puedes configurar el escalado automático aquí, por ejemplo, basado en el uso de CPU.
8.  Revisa la configuración y haz clic en **"Create Service"**.

---

### Paso 7: Desplegar y Probar

Una vez que hayas configurado todos los componentes, tu aplicación debería estar lista para desplegarse.

1.  **Verificar el Servicio ECS:**
    *   Navega a la consola de **Amazon ECS**.
    *   Selecciona tu cluster `streamlit-dashboard-cluster`.
    *   Ve a la pestaña **"Services"** y verifica que tu servicio `streamlit-dashboard-service` esté en estado `RUNNING` y que el número de tareas deseadas (`Desired tasks`) coincida con el número de tareas en ejecución (`Running tasks`).
    *   Si el servicio no se inicia o las tareas no se ejecutan, revisa los logs de las tareas en CloudWatch (configurados en la definición de tarea) para identificar errores.

2.  **Acceder a tu Aplicación:**
    *   Navega a la consola de **Amazon EC2**.
    *   En el panel de navegación izquierdo, bajo **"Load Balancing"**, haz clic en **"Load Balancers"**.
    *   Selecciona tu `streamlit-alb`.
    *   Copia el **"DNS name"** del ALB.
    *   Pega este DNS name en tu navegador. Deberías ver tu aplicación Streamlit cargando correctamente.

---

## 2. Despliegue Automatizado (Visión General)

Para un entorno de producción, se recomienda automatizar el proceso de CI/CD (Integración Continua/Despliegue Continuo). Esto implica:

1.  **Control de Versiones:** Tu código fuente se almacena en un repositorio (ej. GitHub, AWS CodeCommit).
2.  **Build:** Cada vez que se realiza un cambio en el código, un servicio de CI/CD (ej. AWS CodeBuild, GitHub Actions) construye automáticamente la imagen de Docker.
3.  **Push a ECR:** La imagen construida se sube automáticamente a Amazon ECR.
4.  **Despliegue a ECS:** El servicio de CI/CD actualiza el servicio ECS para que use la nueva imagen de Docker, lo que provoca un nuevo despliegue de tus tareas de Fargate.

Herramientas comunes para esto incluyen:
*   **AWS CodePipeline + CodeBuild + CodeDeploy:** Una suite completa de AWS.
*   **GitHub Actions:** Para repositorios en GitHub.
*   **GitLab CI/CD, Jenkins, etc.**

La automatización reduce errores manuales y acelera el ciclo de desarrollo y despliegue.