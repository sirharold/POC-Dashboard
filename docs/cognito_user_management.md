# 🔐 Gestión de Usuarios - AWS Cognito User Pool

## Información del User Pool
- **Nombre:** DashboardEpmaps-UserPool
- **ID:** `us-east-1_WpvoVn1ZJ`
- **Región:** us-east-1
- **Dominio de autenticación:** `dashboardepmaps-auth.auth.us-east-1.amazoncognito.com`

## 👤 Usuario Admin Predeterminado
- **Email:** admin@dashboardepmaps.com
- **Password:** AdminPass123
- **Estado:** Activo y confirmado

---

## 🆕 Crear Nuevos Usuarios desde la Consola AWS

### Método 1: Consola Web (Recomendado)

1. **Ir a AWS Cognito:**
   - Abrir [AWS Console](https://console.aws.amazon.com/)
   - Buscar "Cognito" en servicios
   - Seleccionar "User pools"

2. **Seleccionar el User Pool:**
   - Hacer clic en `DashboardEpmaps-UserPool`
   - En la región `us-east-1`

3. **Crear Usuario:**
   - Ir a la pestaña "Users"
   - Hacer clic en "Create user"
   - Llenar los campos:
     ```
     Username: email del usuario
     Email: mismo email
     Password: [Marcar "Set temporary password"]
     Temporary password: TempPass123
     ```
   - Desmarcar "Mark phone number as verified" (no lo usamos)
   - Marcar "Mark email as verified"
   - Hacer clic en "Create user"

4. **Configurar Password Permanente:**
   - Seleccionar el usuario creado
   - Ir a "Actions" → "Set password"
   - Escribir la contraseña permanente
   - Marcar "Set as permanent password"
   - Hacer clic en "Set password"

### Método 2: AWS CLI

```bash
# Crear usuario
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_WpvoVn1ZJ \
  --username usuario@email.com \
  --user-attributes Name=email,Value=usuario@email.com Name=email_verified,Value=true \
  --temporary-password TempPass123 \
  --message-action SUPPRESS \
  --region us-east-1

# Establecer contraseña permanente
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_WpvoVn1ZJ \
  --username usuario@email.com \
  --password PasswordPermanente123 \
  --permanent \
  --region us-east-1
```

---

## 📋 Requisitos de Contraseña

Las contraseñas deben cumplir:
- ✅ **Mínimo 8 caracteres**
- ✅ **Al menos 1 letra mayúscula**
- ✅ **Al menos 1 letra minúscula**
- ✅ **Al menos 1 número**
- ❌ Símbolos especiales (no requeridos)

**Ejemplos válidos:**
- `AdminPass123`
- `UserLogin456`
- `Dashboard789`

---

## 🔧 Gestión de Usuarios Existentes

### Eliminar Usuario
1. En la consola de Cognito, ir a "Users"
2. Seleccionar el usuario
3. "Actions" → "Delete user"
4. Confirmar eliminación

### Resetear Contraseña
1. Seleccionar el usuario
2. "Actions" → "Reset password"
3. Se enviará email con nueva contraseña temporal
4. O usar "Set password" para establecer una directamente

### Deshabilitar/Habilitar Usuario
1. Seleccionar el usuario
2. "Actions" → "Disable user" o "Enable user"

---

## 🌐 URL de Login

**URL completa para acceder al dashboard:**
`https://DashboardEpmaps-ALB-89321072.us-east-1.elb.amazonaws.com`

*Nota: Una vez configurado HTTPS, el sistema redirigirá automáticamente a la página de login de Cognito antes de permitir acceso al dashboard.*

---

## ⚠️ Notas Importantes

1. **Emails:** Deben ser emails válidos ya que Cognito puede enviar notificaciones
2. **Usernames:** Por defecto configurado para usar emails como username
3. **Verificación:** Los emails se marcan como verificados automáticamente
4. **Seguridad:** Cambiar las contraseñas por defecto en producción
5. **Límites:** El plan gratuito de Cognito permite hasta 50,000 usuarios activos mensuales

---

## 🛠️ Troubleshooting

### Error: "User already exists"
- El email ya está registrado
- Verificar en la lista de usuarios
- Usar un email diferente

### Error: "Password does not meet requirements"
- Verificar que cumple todos los requisitos
- Incluir mayúscula, minúscula y número
- Mínimo 8 caracteres

### Usuario no puede hacer login
- Verificar que el estado sea "Confirmed"
- Verificar que la contraseña sea permanente
- Verificar que el usuario esté habilitado

---

*Documento creado: 23 de septiembre 2025*
*Última actualización: 23 de septiembre 2025*