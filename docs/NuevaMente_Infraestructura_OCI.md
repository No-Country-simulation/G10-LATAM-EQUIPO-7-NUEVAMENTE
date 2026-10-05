# NuevaMente — Infraestructura OCI

**Proyecto:** NuevaMente  
**Fecha de actualización:** 30 de septiembre de 2026  
**Objetivo:** documentar únicamente los recursos OCI, accesos, red y seguridad de la infraestructura base.

> Este documento no describe Docker, la topología interna de servicios ni el proceso de despliegue.  
> Para esos temas consultar:
> - `NuevaMente_Arquitectura_OCI_Actual.md`
> - `NuevaMente_Despliegue_Docker_CICD.md`

---

# 1. Distribución de infraestructura

NuevaMente utiliza actualmente recursos en dos entornos OCI distintos:

```text
OCI de Matias — Chile Central (Santiago)
└── VM Oracle Linux
    └── IP pública reservada: 155.181.154.104

OCI de Tara — Colombia Central (Bogotá)
└── Object Storage
    └── bucket-nuevamente-2026
```

La VM y el bucket no necesitan pertenecer a la misma tenancy. El Backend accede al bucket mediante OCI SDK y API Signing Keys de la tenancy donde vive Object Storage.

---

# 2. Object Storage

## 2.1 Bucket

```text
Bucket:      bucket-nuevamente-2026
Namespace:   axrhuqxl8oyi
Región:      sa-bogota-1
Región UI:   Colombia Central (Bogotá)
```

Configuración confirmada:

```text
Storage tier:          Standard
Visibilidad:           Privado
Cifrado:               Clave gestionada por Oracle
Auto-Tiering:          Desactivado
Eventos de objetos:    Desactivado
Versionado de objetos: Desactivado
```

El bucket no debe exponerse públicamente.

---

# 3. Identidad técnica para Object Storage

```text
Identity Domain: Default
Usuario:         nuevamente-backend
Grupo IAM:       NuevaMente-Backend
```

OCID del usuario:

```text
ocid1.user.oc1..aaaaaaaam3af4ix75zen4gcfgawsmjsbbj6vofvw66cdmajbkps46grztama
```

Tenancy donde vive el bucket:

```text
ocid1.tenancy.oc1..aaaaaaaa64x5krjwhatofelx3gan3cezqomlmm2lkott6ia2wihejclkfw3a
```

El usuario técnico se autentica mediante API Signing Keys.

---

# 4. Política IAM del bucket

Política:

```text
NuevaMente-Backend-ObjectStorage
```

Reglas configuradas:

```text
Allow group 'Default'/'NuevaMente-Backend' to read buckets in tenancy where target.bucket.name = 'bucket-nuevamente-2026'

Allow group 'Default'/'NuevaMente-Backend' to manage objects in tenancy where target.bucket.name = 'bucket-nuevamente-2026'
```

Esto permite consultar el bucket y gestionar objetos únicamente dentro de `bucket-nuevamente-2026`.

---

# 5. Autenticación OCI mediante API Signing Keys

Cada desarrollador que necesite acceso directo al bucket desde local debe usar su propio par de claves.

Flujo:

```text
Generar par de claves
→ conservar la privada localmente
→ registrar únicamente la pública en OCI
→ obtener fingerprint
→ configurar ~/.oci/config local
```

La clave privada:

```text
NO se comparte
NO se envía por canales de mensajería
NO se sube a Git
NO se almacena en documentación
```

Plantilla de configuración:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaam3af4ix75zen4gcfgawsmjsbbj6vofvw66cdmajbkps46grztama
fingerprint=<FINGERPRINT>
tenancy=ocid1.tenancy.oc1..aaaaaaaa64x5krjwhatofelx3gan3cezqomlmm2lkott6ia2wihejclkfw3a
region=sa-bogota-1
key_file=<RUTA_LOCAL_A_LA_CLAVE_PRIVADA>
```

Variables asociadas al bucket:

```env
OCI_NAMESPACE=axrhuqxl8oyi
OCI_BUCKET_NAME=bucket-nuevamente-2026
OCI_REGION=sa-bogota-1
```

---

# 6. API Keys registradas

Clave inicial de administración:

```text
Fingerprint: 1c:de:d5:25:c1:64:11:05:17:93:30:3f:44:5c:ec:1a
```

Clave de JSarabino:

```text
Fingerprint: 48:58:2a:58:4d:b6:af:90:8e:65:e6:b0:3a:ff:79:f6
```

Las claves privadas correspondientes permanecen bajo control de cada propietario y fuera del repositorio.

---

# 7. Máquina virtual OCI

La VM fue creada en la cuenta OCI de Matias.

```text
Región observada: Chile Central (Santiago)
Sistema operativo: Oracle Linux 9.8
IP privada:       10.0.0.213
IP pública:       155.181.154.104
Tipo IP pública:  Reserved
```

Elementos de red confirmados:

```text
VCN:    vcn-20260923-1652
Subnet: subnet-20260923-1652
VNIC:   VNIC-NuevaMente
```

La subred dispone de conectividad a Internet mediante Internet Gateway y tabla de rutas.

---

# 8. Acceso SSH a la VM

Usuario de Oracle Linux:

```text
opc
```

Conexión desde Windows PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\nuevamente_oci" opc@155.181.154.104
```

La clave privada local se mantiene fuera del repositorio.

Fingerprint ED25519 observado para la VM:

```text
SHA256:As6EQXC6oqbtiW5xyppES4mkuam4C2bqj+TUdxYvUK4
```

Si esta huella cambia inesperadamente, debe verificarse la instancia antes de aceptar una nueva.

---

# 9. Red y exposición pública

Hay dos capas independientes de control de red:

```text
1. Firewall del sistema operativo
2. Security List / NSG de OCI
```

En Oracle Linux están habilitados:

```text
ssh
http
```

La URL pública actual de NuevaMente es:

```text
http://155.181.154.104
```

La apertura o modificación de reglas de red OCI corresponde a la tenancy propietaria de la VM.

Las credenciales OCI del bucket no otorgan permisos sobre la red de la VM, porque pertenecen a otra tenancy.

---

# 10. Seguridad y secretos

Puede documentarse:

```text
bucket
namespace
region
OCIDs
fingerprints
IP pública y privada
nombres de VCN/Subnet/VNIC
SSH public key
```

Debe permanecer privado:

```text
OCI API private keys
SSH private key
passwords
tokens
secrets de LLM
credenciales de BD
secrets de CI/CD
.env productivos
```

Regla:

```text
ninguna clave privada
ningún token
ninguna contraseña
→ Git
```

---

# 11. Runbook — agregar acceso OCI a un desarrollador

```text
1. El desarrollador genera un par de claves.
2. Conserva la privada.
3. Envía únicamente la pública.
4. Administración registra la pública en:
   Default → Users → nuevamente-backend → API Keys.
5. OCI genera fingerprint.
6. Administración entrega:
   user
   tenancy
   region
   fingerprint
   namespace
   bucket
7. El desarrollador configura su key_file local.
8. Se prueba acceso al bucket.
```

---

# 12. Runbook — entrar a la VM

Desde PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\nuevamente_oci" opc@155.181.154.104
```

Verificación básica:

```bash
whoami
hostname
uname -a
```

---

# 13. Estado actual de infraestructura OCI

```text
Object Storage      operativo
IAM                 operativo
API Signing Keys    operativo
VM                  operativa
IP reservada        operativa
SSH                 operativo
HTTP público        operativo
```

La ejecución de aplicaciones dentro de la VM se documenta por separado en la arquitectura y el documento de despliegue.
