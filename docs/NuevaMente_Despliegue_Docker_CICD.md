# NuevaMente — Arquitectura de despliegue y contenerización

**Proyecto:** NuevaMente  
**Fecha:** 28 de septiembre de 2026  
**Alcance:** decisiones y pendientes posteriores al documento `NuevaMente_Infraestructura_OCI.md`

> Este documento **no repite** la información ya consolidada sobre bucket, IAM, API Keys, VM, red, SSH, IPs o acceso OCI.  
> Su objetivo es dejar por escrito lo definido después del análisis de **Docker, persistencia, servicios, configuración por entorno y CI/CD**.

---

# 1. Objetivo de esta etapa

La infraestructura base de OCI ya existe. El trabajo actual pasa a ser:

```text
Código del repositorio
        ↓
contenedores
        ↓
Docker Compose
        ↓
VM OCI
        ↓
Nginx / acceso público
        ↓
CI/CD desde GitHub
```

El criterio general es mantener una arquitectura suficientemente limpia para integración y despliegue, sin reproducir infraestructura empresarial innecesaria para el hackathon.

---

# 2. Dirección general acordada

La dirección de despliegue es:

```text
GitHub
  ↓
GitHub Actions
  ↓
validaciones / tests
  ↓
build de imágenes Docker
  ↓
GHCR
  ↓
VM OCI
  ↓
Docker Compose
```

La VM no debería ejecutar manualmente cada aplicación instalando dependencias una por una.

Cada servicio llevará sus propias dependencias dentro de su imagen Docker.

Por tanto, si se mantiene este enfoque:

- Python de Backend, Agentes y Data/IA vive dentro de sus imágenes;
- las dependencias Python se instalan durante el build;
- el host necesita principalmente Docker / Docker Compose y la configuración de entrada pública;
- MySQL deja de ser obligatorio en Sprint 2 porque Backend ya implementó SQLite.

---

# 3. Arquitectura objetivo actual

```text
Internet
   │
   ▼
Nginx
   │
   ├── Frontend
   │
   └── Backend API
            │
            ├── OCI Object Storage
            ├── SQLite persistente
            └── Agentes / RAG
                    │
                    ├── ChromaDB persistente
                    └── Data / IA   [integración posterior]
```

Principio de exposición:

```text
Público:
- entrada web
- Backend a través de Nginx, cuando corresponda

Interno:
- Agentes / RAG
- Data / IA
- puertos internos de los contenedores
```

No se plantea exponer directamente Agentes, ChromaDB o Data/IA a Internet salvo que aparezca una necesidad funcional concreta.

---

# 4. Docker: criterio adoptado

Los contenedores se usarán para aislar:

- runtime;
- dependencias;
- configuración de ejecución;
- proceso de cada servicio.

Las imágenes **no deben contener**:

- claves privadas;
- tokens;
- `.env` productivos;
- bases de datos persistentes;
- ChromaDB persistente;
- credenciales OCI.

Persistencia y secretos deben quedar fuera del ciclo de vida del contenedor.

---

# 5. Frontend

## Estado actual revisado en `QA`

El frontend actual es:

```text
HTML
CSS
JavaScript ES Modules
```

No es React y actualmente no necesita Node para funcionar en runtime.

Se detectó que la URL de Backend está actualmente definida en configuración como:

```text
http://localhost:8000
```

## Decisión de Infra

Infra **no va a imponer la implementación concreta** al equipo Frontend.

El requisito es únicamente:

> La URL o destino del Backend no debe quedar hardcodeado en el código y debe poder configurarse según el entorno.

Frontend decidirá si utiliza:

- Vite;
- `.env`;
- configuración runtime;
- rutas relativas;
- otra solución equivalente.

Vite fue planteado como una opción de bajo impacto, pero no se fija como decisión obligatoria desde Infra.

## Producción

Infra puede soportar cualquiera de estos dos escenarios:

```text
Frontend → /api → Nginx → Backend
```

o:

```text
Frontend → URL configurable de Backend
```

La elección del mecanismo queda en Frontend. Nginx se adaptará al contrato final.

## Persistencia

Frontend no requiere volumen persistente.

---

# 6. Backend API

## Estado actual revisado en `QA`

Stack actual:

```text
Python >= 3.11
FastAPI
Uvicorn
Pydantic Settings
OCI Python SDK
SQLite
pytest
Ruff
```

El Backend ya tiene:

```text
GET /api/v1/health
```

lo cual permite utilizar healthchecks durante despliegue.

También tiene configuración por variables de entorno y `.env`.

## Docker

Backend es actualmente el servicio más listo para dockerizar.

El contenedor deberá ejecutar FastAPI/Uvicorn y escuchar internamente en su puerto configurado.

No es necesario publicar directamente el puerto de Uvicorn a Internet si Nginx será la entrada pública.

---

# 7. Persistencia de Backend: SQLite

Se decidió **mantener SQLite durante el hackathon**.

Motivos:

- ya está implementado;
- ya está probado;
- el modelo actual no requiere capacidades avanzadas de MySQL;
- migrar a MySQL implicaría trabajo adicional en Backend;
- `repository_factory.py` actualmente solo implementa SQLite.

Por tanto, MySQL deja de ser requisito inmediato de Infra para Sprint 2.

## Persistencia

El archivo SQLite **no debe quedar únicamente dentro del contenedor**.

Conceptualmente:

```text
VM
└── datos persistentes
     └── nuevamente.db
            ▲
            │ mount
            ▼
Backend container
└── storage/nuevamente.db
```

El contenedor puede ser reemplazado sin perder la base.

## Upload temporal

El directorio usado para staging temporal de documentos no necesita persistencia.

El flujo actual es:

```text
upload
→ archivo temporal
→ procesamiento / OCI
→ eliminación del temporal
```

Por tanto, ese almacenamiento puede permanecer efímero dentro del contenedor.

---

# 8. Credenciales OCI dentro de Docker

Backend necesita acceso a OCI Object Storage.

La configuración y clave privada **no se incluirán en la imagen**.

Se usará el principio:

```text
VM
└── secretos OCI
      │
      │ mount read-only
      ▼
Backend container
```

Backend ya permite configurar la ruta del archivo OCI mediante variable de entorno, por lo que no requiere una reestructuración para este punto.

La ruta interna del contenedor será definida al construir el Compose definitivo.

---

# 9. Comunicación Backend ↔ Agentes

Sprint 2 ya define esta integración como responsabilidad de Backend y Agentes.

Infra no define el contrato funcional.

El requisito para despliegue es que Backend no tenga una URL de Agentes hardcodeada.

Conceptualmente:

```env
AGENTS_URL=http://...
```

Ejemplo por entorno:

```text
Local:
Backend → localhost:<puerto-agentes>

Docker:
Backend → http://agents:<puerto>
```

El nombre y puerto definitivos se cerrarán cuando Agentes publique su servicio HTTP.

Dentro de Docker, la comunicación se realizará por red interna y no requiere publicar Agentes a Internet.

---

# 10. Agentes / RAG

## Estado actual revisado en `QA`

Actualmente Agentes todavía es código Python invocable y **no un servicio HTTP**.

El Sprint 2 contempla precisamente la creación del endpoint de indexación y los contratos de generación.

Por tanto, el Dockerfile definitivo de Agentes debe esperar a que quede claro:

- entrypoint HTTP;
- framework/servidor utilizado;
- puerto;
- healthcheck.

## Dependencias

El contenedor será más pesado que Backend porque incluye:

```text
ChromaDB
sentence-transformers
modelo de embeddings
pypdf
langchain-text-splitters
```

También debe definirse con qué versión de Python está siendo validado el módulo.

---

# 11. Persistencia de Agentes: ChromaDB

Agentes utiliza actualmente:

```text
chromadb.PersistentClient(...)
```

con una ruta local de Vector Store.

Esa información **sí debe persistir fuera del contenedor**.

Conceptualmente:

```text
VM
└── chroma_db
      ▲
      │ mount
      ▼
Agentes container
```

Si el contenedor se reemplaza, los embeddings y colecciones no deben desaparecer.

---

# 12. Configuración de Agentes

Actualmente `rag/config.py` contiene valores centralizados pero definidos directamente en código, entre ellos:

- `chunk_size`;
- `chunk_overlap`;
- `top_k_default`;
- modelo de embeddings;
- ruta del Vector Store;
- nombre de colección;
- rutas de datasets.

Se recomendó al equipo revisar cuáles de estos valores deben poder cambiar por entorno.

Especialmente relevantes para Infra:

```text
ruta de ChromaDB
modelo
colección
puerto / host del servicio
claves de proveedor LLM, si aplica
```

No se requiere convertir toda constante en variable de entorno; solo aquello que pueda variar entre ambientes o contenga secretos.

---

# 13. Modelo de embeddings

El modelo configurado actualmente es:

```text
paraphrase-multilingual-mpnet-base-v2
```

Debe contemplarse que el modelo tiene que estar disponible al ejecutar el contenedor.

Pendiente definir si:

- se descarga durante el build;
- se descarga al primer arranque;
- se utiliza un cache persistente.

Esta decisión afecta principalmente tiempo y estabilidad del despliegue.

---

# 14. Data / IA

## Estado actual revisado en `QA`

Data/IA es actualmente un módulo Python orientado a:

- contratos;
- validación;
- Ground Truth;
- métricas;
- evaluación;
- reviewer.

Todavía **no expone un servicio HTTP**.

El Planning de Sprint 2 requiere que Data/IA deje preparado un endpoint de evaluación, por lo que Infra debe esperar ese entrypoint antes de cerrar su contenedor definitivo.

## Dependencias actuales

```text
pandas
openpyxl
requests
beautifulsoup4
pydantic
pytest
jupyter
```

## Persistencia

No se detectó actualmente una necesidad de volumen persistente productivo equivalente a SQLite o ChromaDB.

Los datasets y artefactos de evaluación actuales están versionados en el repositorio.

Si posteriormente el servicio genera artefactos que deban conservarse, se revisará entonces.

## OCI / BD

Data/IA no debe acceder directamente a:

- OCI Object Storage;
- base de datos de negocio.

---

# 15. Configuración y secretos de Data / IA

Actualmente el reviewer no llama directamente a un proveedor LLM.

Si Sprint 2 incorpora un proveedor externo, deberán quedar configurables por entorno:

```text
API key
modelo
endpoint del proveedor
timeouts
```

Las claves se inyectarán desde Infra y nunca irán dentro de la imagen.

---

# 16. Hallazgo de código en Data / IA

Se detectó una inconsistencia actual:

```text
evaluation/reviewer.py
```

importa:

```text
ReviewResult
```

mientras que el schema revisado define:

```text
EvaluacionReviewerContract
```

Debe validarse/corregirse por el equipo Data/IA antes de considerar estable el servicio.

No es todavía un problema de Infra, pero sí puede bloquear el contenedor si el módulo se utiliza como entrypoint.

---

# 17. Persistencia consolidada

| Servicio | Persistencia fuera del contenedor | Estado |
|---|---|---|
| Frontend | No | No requerida |
| Backend uploads temporales | No | Efímero |
| Backend SQLite | Sí | Decidido |
| Backend credenciales OCI | Sí, como secreto/mount | Decidido |
| Agentes ChromaDB | Sí | Decidido |
| Data/IA | No por ahora | Revisar si cambia |
| Imágenes Docker | GHCR | Dirección definida |

---

# 18. Red Docker

La idea es que todos los servicios formen parte de una red interna de Docker Compose.

Ejemplo conceptual:

```text
frontend
backend
agents
data-ai
```

Los servicios podrán resolverse entre ellos por nombre dentro de esa red.

Ejemplo:

```text
backend → http://agents:<puerto>
```

No se fijarán nombres ni puertos definitivos hasta que Agentes y Data/IA cierren sus servicios HTTP.

---

# 19. Nginx

Nginx será la capa de entrada pública.

Responsabilidades esperadas:

```text
servir / enrutar Frontend
enrutar Backend
terminar HTTPS cuando se configure TLS
evitar publicar puertos internos innecesarios
```

Pendiente decidir la topología exacta:

```text
A. Nginx separado como reverse proxy
```

o

```text
B. Nginx integrado al contenedor que sirve el Frontend
```

No es necesario resolverlo todavía para que los equipos continúen desarrollando.

---

# 20. CI/CD

Se reutilizará como referencia el patrón ya utilizado anteriormente, pero simplificado para NuevaMente:

```text
push / PR
   ↓
CI
   ↓
tests / validaciones
   ↓
build Docker
   ↓
GHCR
   ↓
deploy por SSH
   ↓
docker compose pull / up
   ↓
healthcheck
```

## Validaciones disponibles actualmente

### Backend

```text
Ruff
Pytest
```

### Agentes

```text
Pytest
```

### Data / IA

```text
Pytest
```

### Frontend

Dependerá de la decisión final del equipo sobre Vite/build.

## Versionado de imágenes

Se mantiene como buena práctica utilizar tags inmutables por commit, por ejemplo:

```text
sha-<commit>
```

además de cualquier tag de conveniencia que se decida utilizar.

Esto facilita rollback sin recompilar.

---

# 21. Dockerfiles y Compose

Al momento de este análisis no se detectaron Dockerfiles ni Docker Compose en la rama `QA`.

Estado esperado:

### Backend

Puede comenzar a dockerizarse con el código actual.

### Frontend

Conviene esperar la decisión final sobre Vite/build antes de cerrar su imagen.

### Agentes

Esperar:

- endpoint HTTP;
- puerto;
- versión de Python;
- configuración externalizable.

### Data / IA

Esperar:

- endpoint HTTP;
- puerto;
- entrypoint definitivo.

### Compose

Debe construirse cuando los contratos mínimos de ejecución de estos servicios estén claros.

---

# 22. Healthchecks

Backend ya dispone de:

```text
GET /api/v1/health
```

Para despliegue estable sería conveniente que Agentes y Data/IA expongan también un endpoint mínimo de salud.

Esto permitirá que Docker/CI/CD valide:

```text
contenedor iniciado
+
servicio realmente respondiendo
```

antes de considerar un despliegue exitoso.

---

# 23. Estructura propuesta en la VM

No implementada todavía. Propuesta de organización:

```text
/opt/nuevamente/
├── compose/
│   └── compose.yaml
├── env/
│   └── archivos de configuración productiva
├── data/
│   ├── backend/
│   │   └── SQLite
│   └── agents/
│       └── ChromaDB
└── secrets/
    └── oci/
```

Los secretos deben tener permisos restringidos y quedar fuera del repositorio.

---

# 24. Tareas pendientes — Infra

## Prioridad alta

- instalar/verificar Docker Engine en la VM;
- instalar/verificar Docker Compose;
- definir estructura de directorios productivos;
- preparar persistencia para SQLite;
- preparar persistencia para ChromaDB;
- preparar montaje seguro de credenciales OCI;
- definir red Docker interna;
- crear Dockerfile de Backend;
- crear primer Compose de integración.

## Cuando los equipos cierren sus servicios

- agregar Agentes al Compose;
- agregar Data/IA al Compose;
- configurar URLs internas mediante variables de entorno;
- configurar healthchecks;
- definir Nginx;
- definir exposición pública definitiva.

## CI/CD

- crear workflows;
- ejecutar tests antes del build;
- publicar imágenes en GHCR;
- desplegar por SSH;
- utilizar tags por SHA;
- validar healthcheck posterior al deploy;
- preparar rollback por tag anterior.

---

# 25. Dependencias pendientes por equipo

## Frontend

Infra espera:

- eliminación del Backend hardcodeado;
- mecanismo configurable por entorno;
- decisión final sobre Vite/build.

No se impone la solución.

## Backend

Infra espera:

- transporte HTTP real hacia Agentes;
- variable configurable para URL de Agentes;
- modelo de datos actualizado de Sprint 2.

SQLite se mantiene.

## Agentes

Infra espera:

- servicio HTTP;
- puerto;
- endpoint de indexación;
- endpoints/contrato de generación;
- healthcheck;
- versión de Python;
- rutas configurables para persistencia;
- definición de secretos/modelo LLM si aplica.

## Data / IA

Infra espera:

- servicio HTTP;
- puerto;
- endpoint de evaluación;
- healthcheck;
- corrección/validación del schema del reviewer;
- configuración externa de proveedor LLM si se incorpora.

---

# 26. Orden sugerido de implementación de Infra

```text
1. Docker + Compose en la VM
2. Dockerizar Backend
3. Persistencia SQLite + credenciales OCI
4. Levantar Backend y validar /health
5. Integrar Frontend cuando cierre configuración/build
6. Incorporar Agentes cuando exista servicio HTTP
7. Persistir ChromaDB
8. Incorporar Data/IA cuando exista endpoint
9. Nginx y rutas públicas
10. CI/CD completo
11. pruebas end-to-end
```

Este orden permite avanzar sin esperar a que todos los equipos terminen simultáneamente.

---

# 27. Decisiones que actualizan supuestos anteriores

A partir de este análisis:

### MySQL

```text
Antes:
previsto para la VM

Ahora:
no requerido para Sprint 2
```

Se mantiene SQLite porque es la implementación real existente.

### Python en la VM

```text
Antes:
instalar runtimes de aplicaciones en el host

Ahora:
si se consolida Docker, Python vive dentro de las imágenes
```

No es necesario que el host replique los entornos Python de cada servicio.

### Agentes y Data/IA públicos

No se considera necesario publicar directamente estos servicios a Internet.

La comunicación prevista es interna entre contenedores.

---

# 28. Estado actual resumido

```text
OCI base
→ ya documentado por separado

Docker
→ arquitectura definida
→ instalación pendiente

Frontend
→ requisito de configuración definido
→ solución técnica queda al equipo

Backend
→ listo para iniciar dockerización
→ SQLite persistente
→ OCI secrets externos
→ healthcheck existente

Agentes
→ requiere servicio HTTP
→ ChromaDB persistente
→ configuración por entorno pendiente

Data/IA
→ requiere servicio HTTP
→ sin persistencia crítica por ahora
→ posible configuración LLM pendiente

Nginx
→ requerido como entrada pública
→ topología exacta pendiente

CI/CD
→ patrón definido
→ implementación pendiente
```

---

# 29. Criterio rector

La infraestructura debe facilitar la integración sin apropiarse de decisiones internas de cada área.

Infra define:

```text
cómo se ejecutan
cómo se conectan
qué se persiste
qué se expone
cómo reciben configuración
cómo se despliegan
```

Cada equipo define:

```text
contratos funcionales
estructura interna
frameworks
lógica de negocio
modelos de dominio
implementación concreta
```

El objetivo inmediato no es añadir capas innecesarias, sino disponer de un entorno compartido, reproducible y desplegable donde el flujo completo del Sprint 2 pueda integrarse y probarse.
