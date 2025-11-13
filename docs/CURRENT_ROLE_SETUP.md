# Configuración Completa del Rol RecolectorDeDashboard

## ⚠️ Importante: Trust Policy vs Permissions Policy

El JSON que tienes es la **Trust Policy** (define **quién** puede asumir el rol).
Los permisos SSM van en una **Permissions Policy** (define **qué** puede hacer el rol).

**NO modifiques la Trust Policy**. Solo necesitas agregar una nueva Permissions Policy.

---

## 1. Trust Policy (MANTENER COMO ESTÁ)

Esta política está correcta, no la modifiques:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::687634808667:root",
                    "arn:aws:iam::011528297340:role/morrisopazo"
                ]
            },
            "Action": "sts:AssumeRole",
            "Condition": {}
        }
    ]
}
```

---

## 2. Permissions Policy (AGREGAR NUEVA)

Debes agregar esta nueva política de permisos al rol:

### Opción A: Desde la Consola AWS (Recomendado)

1. Ve a: **IAM** → **Roles** → **RecolectorDeDashboard**
2. En la pestaña **"Permissions"** (no Trust relationships)
3. Clic en **"Add permissions"** → **"Create inline policy"**
4. Clic en la pestaña **"JSON"**
5. Pega el siguiente JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMReadFilePermissions",
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation",
        "ssm:ListCommandInvocations",
        "ssm:DescribeInstanceInformation"
      ],
      "Resource": [
        "arn:aws:ec2:us-east-1:011528297340:instance/*",
        "arn:aws:ssm:us-east-1:011528297340:*",
        "arn:aws:ssm:us-east-1::document/AWS-RunShellScript",
        "arn:aws:ssm:us-east-1::document/AWS-RunPowerShellScript"
      ]
    }
  ]
}
```

6. Clic en **"Review policy"**
7. Nombre: `SSMReadFilesPermissions`
8. Clic en **"Create policy"**

### Opción B: Desde AWS CLI

```bash
aws iam put-role-policy \
  --role-name RecolectorDeDashboard \
  --policy-name SSMReadFilesPermissions \
  --policy-document file://docs/SSM_PERMISSIONS_POLICY.json
```

---

## 3. Estructura Final del Rol

Después de aplicar los cambios, tu rol debería tener:

### Trust Policy (quién puede asumir el rol):
- ✅ `arn:aws:iam::687634808667:root`
- ✅ `arn:aws:iam::011528297340:role/morrisopazo`

### Permissions Policies (qué puede hacer el rol):
- ✅ Políticas existentes de EC2, CloudWatch, etc. (las que ya tenía)
- ✅ **Nueva:** `SSMReadFilesPermissions` (para leer archivos via SSM)

---

## 4. Verificar la Configuración

Después de agregar los permisos:

1. Ve a: **IAM** → **Roles** → **RecolectorDeDashboard**
2. En la pestaña **"Permissions"**, deberías ver:
   - Las políticas que ya tenía el rol
   - **Nueva:** `SSMReadFilesPermissions` (inline policy)

3. En la pestaña **"Trust relationships"**, debería seguir igual (sin cambios)

---

## 5. Verificar en el Dashboard

Una vez aplicados los cambios:

1. Ir al Dashboard
2. Abrir detalles de una instancia
3. Sección "📄 Visor de Logs SAP (available.log)"
4. Hacer clic en "📥 Descargar"
5. Debe funcionar sin errores de permisos

---

## Resumen de Acciones

- [ ] **NO** modificar Trust Policy (dejarla como está)
- [ ] Agregar nueva Permissions Policy con permisos SSM
- [ ] Verificar que las instancias tengan SSM Agent instalado
- [ ] Verificar que las instancias tengan IAM Instance Profile con `AmazonSSMManagedInstanceCore`
- [ ] Probar la descarga de logs en el Dashboard
