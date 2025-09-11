# Despliegue en AWS EC2 para Beta 1

Esta guía detalla los pasos para desplegar la aplicación del dashboard en una instancia de Amazon EC2. Este método es ideal para un entorno beta, ya que nos da control total sobre el servidor para instalar dependencias clave como la `aws-cli`.

---

### Paso 1: Crear un Rol de IAM (Mejor Práctica de Seguridad)

Para evitar almacenar credenciales de AWS en el servidor, creamos un rol que le otorga los permisos necesarios de forma segura.

1.  **Navega a IAM** en la consola de AWS.
2.  **Crea un nuevo Rol**.
3.  **Entidad de confianza:** Selecciona **"Servicio de AWS"**.
4.  **Caso de uso:** Selecciona **"EC2"**.
5.  **Añadir permisos:** Busca y añade las siguientes políticas administradas por AWS:
    *   `CloudWatchReadOnlyAccess`
    *   `AmazonEC2ReadOnlyAccess`
6.  **Nombra el rol:** Usa un nombre descriptivo, como `DashboardAppBetaRole`, y finaliza la creación.

---

### Paso 2: Lanzar la Instancia EC2

Este es el servidor virtual que ejecutará la aplicación.

1.  **Navega a EC2** en la consola de AWS y haz clic en **"Lanzar instancia"**.
2.  **Nombre:** `Dashboard-Beta-Server`.
3.  **AMI (Imagen de Máquina de Amazon):** Selecciona **Amazon Linux 2023 AMI**. Es gratuita y ya incluye la AWS CLI v2.
4.  **Tipo de instancia:** `t4g.small` o `t3.micro` son opciones económicas y suficientes para la beta.
5.  **Par de claves (key pair):** Asigna un par de claves existente o crea uno nuevo para poder conectarte al servidor vía SSH.
6.  **Configuración de red (Security Group):**
    *   Crea un nuevo grupo de seguridad.
    *   Añade una regla de entrada para **SSH (puerto 22)**. En "Origen", selecciona **"Mi IP"** por seguridad.
    *   Añade otra regla para **TCP Personalizado** en el **puerto 8501** (el puerto de Streamlit). En "Origen", selecciona **"Cualquier lugar" (`0.0.0.0/0`)** para que tu equipo pueda acceder.
7.  **Detalles avanzados:** Expande esta sección.
    *   En **"Perfil de instancia de IAM"**, selecciona el rol que creaste en el Paso 1 (`DashboardAppBetaRole`). **Este es un paso crucial.**
8.  **Lanza la instancia.**

---

### Paso 3: Conectar e Instalar Dependencias

1.  Una vez que el estado de la instancia sea "En ejecución", selecciónala y haz clic en **"Conectar"**. Sigue las instrucciones para usar SSH.
2.  Una vez conectado al servidor, ejecuta los siguientes comandos en la terminal:

    ```bash
    # 1. Actualizar el sistema operativo del servidor
    sudo yum update -y

    # 2. Instalar Git para clonar el código y Pip para las dependencias de Python
    sudo yum install git python3-pip -y

    # 3. Clonar el repositorio del proyecto (reemplaza con la URL de tu repo)
    git clone https://github.com/tu-usuario/tu-repositorio.git dashboard
    cd dashboard

    # 4. Instalar las dependencias de Python definidas en el proyecto
    pip3 install -r requirements.txt
    ```

---

### Paso 4: Ejecutar la Aplicación

Para iniciar la aplicación y mantenerla corriendo, sigue estos pasos.

1.  Usa el comando `nohup` para que la aplicación no se detenga cuando te desconectes del servidor:

    ```bash
    nohup streamlit run app.py &
    ```

2.  La aplicación se está ejecutando en segundo plano.
3.  **Para acceder a ella:**
    *   Vuelve a la consola de EC2.
    *   Selecciona tu instancia y copia su **"Dirección IPv4 pública"**.
    *   Abre tu navegador y pega la dirección seguida del puerto 8501.

    **Ejemplo:** `http://54.123.45.67:8501`

¡Listo! La versión beta de tu aplicación está desplegada y lista para recibir feedback.
