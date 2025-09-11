# Despliegue con AWS App Runner (Estrategia Recomendada)

Esta guía detalla cómo desplegar la aplicación usando **AWS App Runner**, un servicio totalmente gestionado que es más moderno, económico y escalable que una instancia EC2 para este caso de uso.

**Ventajas:**
- **Costo Eficiente:** App Runner puede escalar a cero, por lo que solo pagas cuando la aplicación está en uso.
- **Totalmente Gestionado:** AWS se encarga del servidor, el balanceo de carga, la seguridad y la escalabilidad.
- **Despliegue Sencillo:** Se despliega directamente desde tu repositorio de código.

---

### Prerrequisitos

1.  **Código Refactorizado:** La aplicación ha sido actualizada para usar la librería `boto3` en lugar de `aws-cli`.
2.  **`Dockerfile` Existente:** El proyecto ahora incluye un `Dockerfile` en su raíz, que le dice a App Runner cómo construir la aplicación.
3.  **Repositorio de Código:** Tu código debe estar en un repositorio de GitHub (o Bitbucket).

---

### Paso 1: Crear un Rol de IAM para App Runner

App Runner necesita permisos para poder llamar a los servicios de EC2 y CloudWatch en tu nombre.

1.  **Ve a IAM** en tu consola de AWS y crea un **nuevo Rol**.
2.  **Entidad de confianza:** Selecciona **"Servicio de AWS"**.
3.  **Caso de uso:** Busca y selecciona **"EC2"** en la lista. (Sí, EC2. App Runner asumirá este rol como si fuera una instancia).
4.  **Añadir permisos:** Busca y añade las mismas políticas que antes:
    *   `CloudWatchReadOnlyAccess`
    *   `AmazonEC2ReadOnlyAccess`
5.  **Nombra el rol:** Usa un nombre descriptivo, como `AppRunnerServiceRole`, y finaliza la creación.

---

### Paso 2: Configurar y Lanzar el Servicio en App Runner

1.  **Navega a AWS App Runner** en la consola.
2.  Haz clic en **"Crear un servicio"**.
3.  **Fuente y despliegue:**
    *   **Fuente:** Selecciona **"Repositorio de código fuente"**.
    *   **Conexión:** Si es la primera vez, crea una nueva conexión a tu cuenta de GitHub. Autoriza a AWS para que pueda ver tus repositorios.
    *   **Repositorio:** Elige el repositorio de tu proyecto y la rama (ej. `main`).
    *   **Despliegue:** Selecciona **"Automático"** para que cada cambio en la rama se despliegue solo.
4.  **Configuración de la compilación (Build):**
    *   En la sección "Configurar la compilación", selecciona **"Usar un Dockerfile"**.
    *   App Runner detectará automáticamente el `Dockerfile` en tu repositorio.
5.  **Configuración del servicio:**
    *   **Nombre del servicio:** Elige un nombre, como `dashboard-epmaps-beta`.
    *   **Puerto:** Escribe `8501`.
    *   **Rol de instancia:** En la sección de "Seguridad", busca y selecciona el rol que creaste en el Paso 1 (`AppRunnerServiceRole`).
6.  **Revisa y crea:** Haz clic en **"Siguiente"**, revisa la configuración y finalmente en **"Crear y desplegar"**.

---

### Paso 3: Acceder a la Aplicación

1.  **Espera:** El primer despliegue tardará varios minutos. App Runner está construyendo el contenedor desde tu `Dockerfile` y poniéndolo en línea.
2.  **Accede a la URL:** Una vez que el estado del servicio sea **"Running"**, App Runner te proporcionará un **"Dominio predeterminado"** (una URL terminada en `.awsapprunner.com`).

    `https://<id_unico>.awsapprunner.com`

Cualquier persona con esta URL podrá acceder a la versión beta de tu aplicación. La URL ya es segura (HTTPS).
