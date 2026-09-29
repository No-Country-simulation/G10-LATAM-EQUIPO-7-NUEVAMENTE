# NuevaMente — Infraestructura OCI

**Proyecto:** NuevaMente  
**Fecha de actualización:** 28 de septiembre de 2026

> Documento consolidado exclusivamente de infraestructura.  
> **No contiene claves privadas.** Las claves privadas, contraseñas y tokens no deben almacenarse en el repositorio ni en este documento.

---

# 1. OCI Object Storage

## 1.1 Bucket

```text
Bucket:      bucket-nuevamente-2026
Namespace:   axrhuqxl8oyi
Región:      sa-bogota-1
Región UI:   Colombia Central (Bogotá)
```

Configuración confirmada:

```text
Storage tier:                     Standard
Visibilidad:                      Privado
Cifrado:                          Clave gestionada por Oracle
Auto-Tiering:                     Desactivado
Eventos de objetos:               Desactivado
Versionado de objetos:            Desactivado
```

El bucket no necesita ser público.

---

# 2. Identidad técnica de OCI

Se creó una identidad técnica específica para el acceso del Backend a Object Storage.

```text
Identity Domain:  Default
Usuario:          nuevamente-backend
Grupo IAM:        NuevaMente-Backend
```

OCID del usuario:

```text
ocid1.user.oc1..aaaaaaaam3af4ix75zen4gcfgawsmjsbbj6vofvw66cdmajbkps46grztama
```

Tenancy donde vive el bucket:

```text
ocid1.tenancy.oc1..aaaaaaaa64x5krjwhatofelx3gan3cezqomlmm2lkott6ia2wihejclkfw3a
```

El usuario técnico se utiliza para autenticación API mediante API Signing Keys.

---

# 3. Política IAM del bucket

Nombre de política:

```text
NuevaMente-Backend-ObjectStorage
```

Políticas configuradas:

```text
Allow group 'Default'/'NuevaMente-Backend' to read buckets in tenancy where target.bucket.name = 'bucket-nuevamente-2026'

Allow group 'Default'/'NuevaMente-Backend' to manage objects in tenancy where target.bucket.name = 'bucket-nuevamente-2026'
```

Esto permite al grupo:

- consultar el bucket;
- listar objetos;
- subir archivos;
- leer archivos;
- reemplazar objetos;
- eliminar objetos.

Los permisos quedan restringidos al bucket:

```text
bucket-nuevamente-2026
```

---

# 4. Autenticación OCI mediante API Signing Keys

Cada desarrollador que necesite acceder a Object Storage desde local debe usar su propio par de claves.

Flujo:

```text
Desarrollador genera par de claves
↓
Conserva la clave privada localmente
↓
Envía únicamente la clave pública
↓
La clave pública se registra en:
nuevamente-backend → Claves de API
↓
OCI genera un fingerprint
↓
El desarrollador configura su archivo OCI local
```

La clave privada:

```text
NO se envía por Discord
NO se comparte con otros miembros
NO se sube a Git
NO se almacena en este documento
```

---

# 5. Configuración OCI para acceso desde local

Plantilla:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaam3af4ix75zen4gcfgawsmjsbbj6vofvw66cdmajbkps46grztama
fingerprint=<FINGERPRINT_DE_LA_CLAVE_DEL_DESARROLLADOR>
tenancy=ocid1.tenancy.oc1..aaaaaaaa64x5krjwhatofelx3gan3cezqomlmm2lkott6ia2wihejclkfw3a
region=sa-bogota-1
key_file=<RUTA_LOCAL_A_LA_CLAVE_PRIVADA_PEM>
```

Variables asociadas al bucket:

```env
OCI_NAMESPACE=axrhuqxl8oyi
OCI_BUCKET_NAME=bucket-nuevamente-2026
OCI_REGION=sa-bogota-1
```

`key_file` siempre apunta a la clave privada local del desarrollador.

---

# 6. API Keys registradas

## 6.1 Clave inicial de administración

Fingerprint:

```text
1c:de:d5:25:c1:64:11:05:17:93:30:3f:44:5c:ec:1a
```

La clave privada correspondiente quedó bajo control de administración y no se comparte.

## 6.2 JSarabino

Archivo público registrado:

```text
nuevamente_api_key_public.pem
```

Fingerprint:

```text
48:58:2a:58:4d:b6:af:90:8e:65:e6:b0:3a:ff:79:f6
```

Configuración asociada:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaam3af4ix75zen4gcfgawsmjsbbj6vofvw66cdmajbkps46grztama
fingerprint=48:58:2a:58:4d:b6:af:90:8e:65:e6:b0:3a:ff:79:f6
tenancy=ocid1.tenancy.oc1..aaaaaaaa64x5krjwhatofelx3gan3cezqomlmm2lkott6ia2wihejclkfw3a
region=sa-bogota-1
key_file=<ruta local de SU clave privada>
```

---

# 7. Procedimiento para agregar una nueva API Key

Ruta en OCI:

```text
Identidad y seguridad
→ Dominios
→ Default
→ Usuarios
→ nuevamente-backend
→ Claves de API
→ Agregar clave de API
→ Seleccionar archivo de clave pública
```

Se carga únicamente la clave pública.

Después OCI entrega el fingerprint correspondiente.

Datos a entregar al desarrollador:

```text
user
tenancy
region
fingerprint
namespace
bucket
```

El desarrollador completa localmente:

```text
key_file=<ruta a su propia clave privada>
```

---

# 8. Máquina virtual OCI

La VM fue creada en una cuenta OCI de Matias. 

Región observada:

```text
Chile Central (Santiago)
```

Sistema operativo:

```text
Oracle Linux
```

---

# 9. Red de la VM

Elementos confirmados:

```text
VCN:       vcn-20260923-1652
Subnet:    subnet-20260923-1652
VNIC:      VNIC-NuevaMente
```

La subred fue conectada a Internet mediante:

- Internet Gateway;
- tabla de rutas;
- Network Security Group asociado a la VNIC.

Direcciones:

```text
IP privada:           10.0.0.213
IP pública reservada: 155.181.154.104
```

La IP pública es **Reserved**, no efímera.

---

# 10. Distribución actual de infraestructura

Actualmente la infraestructura está distribuida entre dos entornos OCI:

```text
OCI de Matias  — Chile Central (Santiago)
└── VM Oracle Linux
    └── servicios a desplegar
             │
             │ OCI SDK + API Signing Key
             ▼
OCI de Tara — Colombia Central (Bogotá)
└── Object Storage
    └── bucket-nuevamente-2026
```

La VM y el bucket no necesitan pertenecer a la misma tenancy.

El acceso desde la VM al bucket se autentica con:

```text
user
tenancy
fingerprint
private key
```

de la tenancy donde vive Object Storage.

---

# 11. Acceso SSH a la VM

Usuario de Oracle Linux:

```text
opc
```

IP pública:

```text
155.181.154.104
```

Clave SSH privada local de Tara:

```powershell
$env:USERPROFILE\.ssh\nuevamente_oci
```

Clave pública:

```powershell
$env:USERPROFILE\.ssh\nuevamente_oci.pub
```

Rutas típicas:

```text
C:\Users\<USUARIO>\.ssh\nuevamente_oci
C:\Users\<USUARIO>\.ssh\nuevamente_oci.pub
```

La clave sin `.pub` es privada y no debe compartirse.

---

# 12. Creación de la clave SSH

Comando utilizado en PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null; ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\nuevamente_oci" -C "tara-nuevamente-oci"
```

Fingerprint de la clave pública:

```text
4096 SHA256:Ag0ODfy5YQ9egVzGkSybEZJTy1Hzmad8aNKA7UUrZ44 tara-nuevamente-oci (RSA)
```

---

# 13. Clave SSH pública usada para la VM

```text
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDtEGeH5vZJVKE9CQ/TYPDZBD5J6A2kWBd/XCN6505/aMU7Of070c+3k41CRyYBE/PWwtr0VqPNcawZXPNB0eHqKD40mcN9pmI1Yn1pzNIpNEECU7TZD429mXJqwWgSEHdJfMXdNnemMxwYqtHLhFreF+zVa2hUv2xVakcsQoPyPvMd5Kyn4LNvL6/jeWRMPTkAx4lv7TWYSrkCqA+u6+wkMMNxMMgGLv0hubNKQsj115g0yurGtJlkxRIBbkXZYaKQxQhDIxCUN/831+CZe0qyEey+w8DUcdGLxytI8ZKgk2OIsDoYhdfrF2tC5EImsvqDRBQp5ij0+Qb/LoemKAqgclTHxBsaUP+za+miXxlNpCTYCFi7IYy15iQ/4MltEinwrx7msR1X2xP68VOHoYjkH1VIuAlytT+nfYurWXSlz7S7VltO2CGHrKxLZbTYkj4b0RHeoLwvend99z17s4+9xe84IspFubaY/b3WdDzSp71BvGF3YKLQFdyVDAAtYuG50u6pcdQjNzhwbtjqWO7wG23V4Z7LOvQ5yo2NSmqkXdPq7SOTd755u07a+LUq7cFXZ+NBpwVh17wI0ig+0/oWKULTHvywmYAUgVRK1xke2vVsXb2iF/PqBcEsyaeknrDw2ZMxvkafbHfcrHiexVu9WbcM5/aru1XMfhFBD/09+Q== tara-nuevamente-oci
```

---

# 14. Conexión SSH desde Windows

Comando probado:

```powershell
ssh -i "$env:USERPROFILE\.ssh\nuevamente_oci" opc@155.181.154.104
```

En la primera conexión SSH solicita confirmar la autenticidad del host.

Se acepta con:

```text
yes
```

Fingerprint ED25519 observado para la VM:

```text
SHA256:As6EQXC6oqbtiW5xyppES4mkuam4C2bqj+TUdxYvUK4
```

Si la huella del host cambia inesperadamente en el futuro, debe verificarse la instancia antes de aceptar una nueva.

---

# 15. Comandos básicos de verificación en la VM

```bash
whoami
```

Esperado:

```text
opc
```

También:

```bash
hostname
```

```bash
uname -a
```

Para tareas administrativas:

```bash
sudo <comando>
```

---

# 16. Acceso OCI vs acceso a la VM

Son accesos distintos.

## Consola OCI

El dueño de la tenancy conserva control sobre:

- creación/eliminación de la VM;
- VCN;
- subnet;
- VNIC;
- IP pública;
- reglas de red;
- almacenamiento de bloque;
- configuración de Compute.

## Sistema operativo

El acceso se realiza por SSH:

```text
Tara
→ SSH con clave privada local
→ opc@155.181.154.104
→ sudo
→ administración del entorno
```

No es necesario tener acceso completo a la consola OCI del propietario de la VM para administrar el sistema operativo.

---

# 17. Servicios previstos en la VM

Infraestructura debe preparar:

```text
Python
MySQL
Nginx
Frontend
Backend
Agentes
Data / IA
URLs públicas
CI/CD desde GitHub
```

Esquema previsto:

```text
Internet
   │
   ▼
Reserved Public IP
155.181.154.104
   │
   ▼
Nginx
   ├── Frontend
   ├── Backend API
   ├── Agentes
   └── Data / IA
```

---

# 18. Estado confirmado de infraestructura

Confirmado:

- OCI Object Storage creado.
- Bucket privado operativo.
- Namespace identificado.
- Región identificada.
- Usuario técnico `nuevamente-backend` creado.
- Grupo IAM `NuevaMente-Backend` creado.
- Política IAM restringida al bucket creada.
- API Signing Key de JSarabino registrada.
- VM creada.
- Oracle Linux confirmado.
- Subred con conectividad a Internet.
- IP pública reservada asignada.
- Acceso SSH desde el equipo de Tara probado correctamente.
- Infraestructura base disponible para despliegue.

---

# 19. Pendientes de infraestructura

Pendiente o no confirmado todavía:

- instalación definitiva de Python;
- instalación/configuración de MySQL;
- instalación/configuración de Nginx;
- despliegue estable de Frontend;
- despliegue estable de Backend;
- despliegue de Agentes;
- despliegue de Data/IA;
- URLs públicas por servicio;
- reglas HTTP/HTTPS definitivas;
- certificados TLS;
- CI/CD desde GitHub;
- validación de servicios después del despliegue.

No debe marcarse ninguno como terminado hasta probarlo.

---

# 20. Secretos y configuración

Puede documentarse:

```text
Bucket name
Namespace
Region
User OCID
Tenancy OCID
Fingerprint
SSH public key
Public IP
Private IP
Nombres de VCN/Subnet/VNIC
```

Debe permanecer privado:

```text
OCI API private keys
SSH private key
Passwords
Tokens
Secrets de LLM
Credenciales de BD
Secrets de CI/CD
```

Regla:

```text
ninguna clave privada
ningún token
ninguna contraseña
→ Git
```

---

# 21. Archivos que deben quedar fuera del repositorio

Ejemplo de `.gitignore`:

```gitignore
*.pem
.env
.env.*
!.env.example
```

La clave SSH privada:

```text
nuevamente_oci
```

no debe copiarse dentro del repositorio.

Las claves privadas de OCI deben quedar en rutas locales seguras fuera del proyecto.

---

# 22. Variables de entorno de infraestructura

```env
OCI_NAMESPACE=axrhuqxl8oyi
OCI_BUCKET_NAME=bucket-nuevamente-2026
OCI_REGION=sa-bogota-1
```

También deben mantenerse configurables por entorno:

```text
URLs de servicios
credenciales
rutas
puertos
timeouts
variables de BD
variables de despliegue
```

---

# 23. Runbook — agregar acceso OCI a un desarrollador

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
7. El desarrollador configura:
   key_file=<ruta a su propia clave privada>
8. Se prueba acceso al bucket.
```

---

# 24. Runbook — entrar a la VM

Desde PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\nuevamente_oci" opc@155.181.154.104
```

Verificación:

```bash
whoami
hostname
uname -a
```

---

# 25. Fotografía actual de infraestructura

```text
Object Storage
→ operativo

IAM
→ usuario técnico operativo
→ grupo operativo
→ política restringida al bucket operativa

API Keys
→ mecanismo funcionando

VM
→ creada
→ Oracle Linux
→ red pública
→ IP reservada
→ SSH operativo

Servidor
→ pendiente configuración de servicios

Despliegue
→ pendiente
```
