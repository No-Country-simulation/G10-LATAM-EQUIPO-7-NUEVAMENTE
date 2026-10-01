# NuevaMente — Arquitectura OCI actual

**Proyecto:** NuevaMente  
**Fecha de corte:** 30 de septiembre de 2026  
**Objetivo:** documentar únicamente la topología actual de aplicaciones y sus dependencias dentro del entorno OCI ya desplegado.

> Este documento describe **qué está corriendo y cómo se conecta**.  
> No repite IAM, SSH, creación de recursos OCI ni procedimientos de despliegue.
>
> Ver también:
> - `NuevaMente_Infraestructura_OCI.md`
> - `NuevaMente_Despliegue_Docker_CICD.md`

---

# 1. Vista general

```text
Usuario
  │
  ▼
http://155.181.154.104
  │
  ▼
Frontend + Nginx :80
  │
  ▼
Backend API :8000
  │
  ├── OCI Object Storage
  ├── SQLite persistente
  └── Agentes / RAG :8001
          │
          ├── ChromaDB persistente
          └── Cache de modelos

Data / IA :8002
(servicio interno; integración productiva aún en progreso)
```

Todos los componentes de aplicación corren en una única VM Oracle Linux administrada con Docker Compose.

---

# 2. Servicios desplegados

| Servicio | Tecnología | Puerto | Exposición |
|---|---|---:|---|
| Frontend + Nginx | Vite build + Nginx | 80 | Pública |
| Backend API | FastAPI / Uvicorn | 8000 | Solo VM / red interna |
| Agentes / RAG | FastAPI / Uvicorn | 8001 | Solo VM / red interna |
| Data / IA | FastAPI / Uvicorn | 8002 | Solo VM / red interna |

Los puertos `8000`, `8001` y `8002` no deben publicarse directamente a Internet.

---

# 3. Frontend + Nginx

El contenedor Frontend cumple dos funciones:

```text
servir archivos web
+
actuar como reverse proxy hacia Backend
```

Configuración lógica:

```text
/       → Frontend estático
/api/   → backend:8000/api/
```

El Frontend se construye con Vite y usa:

```env
VITE_API_BASE_URL=/
```

Por tanto, el navegador no conoce la URL interna de Backend.

El límite de carga configurado en Nginx es 10 MB.

---

# 4. Backend API

Backend es el punto central de orquestación de la aplicación.

Responsabilidades actuales:

```text
recepción y validación de documentos
metadata
persistencia SQLite
acceso a OCI Object Storage
orquestación de integraciones
```

Backend es el único servicio de aplicación que accede directamente a OCI Object Storage.

Publicación en host:

```text
127.0.0.1:8000 → container:8000
```

---

# 5. Agentes / RAG

Agentes expone:

```text
POST /api/v1/index
POST /api/v1/generate
```

Indexación:

```text
document_id + file
→ extracción
→ limpieza
→ chunking
→ embeddings
→ ChromaDB
```

El retrieval filtra por `document_id` para evitar mezclar documentos distintos.

La generación todavía utiliza contenido simulado/mock donde corresponde; el servicio está desplegado, pero la integración con un LLM real aún no está finalizada.

Publicación en host:

```text
127.0.0.1:8001 → container:8001
```

---

# 6. Data / IA

Data/IA expone:

```text
GET  /health
POST /evaluate
```

Estado validado:

```text
GET /health                  → 200
POST /evaluate válido        → 501 esperado
POST /evaluate inválido      → 422 esperado
```

El `501` confirma que el contrato y las validaciones están operativos, aunque la lógica real del evaluator todavía no esté conectada al endpoint.

Publicación en host:

```text
127.0.0.1:8002 → container:8002
```

Data/IA no requiere volumen persistente de producción por ahora.

---

# 7. Red Docker interna

Docker Compose crea una red privada donde los servicios se resuelven por nombre:

```text
frontend
backend
agents
data-ia
```

Conectividad comprobada:

```text
backend → http://agents:8001
```

Backend utiliza:

```env
RAG_BASE_URL=http://agents:8001
RAG_INDEX_PATH=/api/v1/index
RAG_TIMEOUT_SECONDS=120
```

La resolución DNS interna y la conectividad HTTP Backend → Agentes están operativas.

---

# 8. Persistencia

| Componente | Ruta VM | Ruta contenedor |
|---|---|---|
| Backend SQLite | `/opt/nuevamente/data/backend` | `/app/storage` |
| Agentes ChromaDB | `/opt/nuevamente/data/agents` | `/app/chroma_db` |
| Cache Hugging Face | `/opt/nuevamente/data/huggingface` | `/root/.cache/huggingface` |
| OCI config | `/opt/nuevamente/secrets/oci/config` | `/run/oci/config:ro` |
| OCI private key | `/opt/nuevamente/secrets/oci/backend.pem` | `/run/oci/backend.pem:ro` |

SQLite y ChromaDB fueron verificados recreando contenedores y comprobando que los datos persistían.

El cache de Hugging Face evita descargar nuevamente el modelo de embeddings en cada recreación.

Modelo actual:

```text
paraphrase-multilingual-mpnet-base-v2
```

---

# 9. OCI Object Storage

Backend accede a:

```text
bucket-nuevamente-2026
namespace: axrhuqxl8oyi
region: sa-bogota-1
```

El acceso utiliza OCI Python SDK y API Signing Keys montadas como secretos read-only.

La carga real de documentos hacia Object Storage fue validada desde la VM.

---

# 10. Estado Backend → Agentes

Infraestructura disponible:

```text
Backend container
→ red Docker
→ agents:8001
→ HTTP operativo
```

También existen en Backend:

```text
HTTPRAGAdapter
RAGIntegrationService
RAG_BASE_URL
RAG_INDEX_PATH
```

Sin embargo, en la versión desplegada todavía no se observa un endpoint público que dispare explícitamente la indexación RAG ni que `/documents` complete ese flujo.

Estado correcto:

```text
Contrato Backend ↔ Agentes        definido
Servicio Agentes HTTP             operativo
Conectividad Docker               operativa
Adapter HTTP Backend              implementado
RAGIntegrationService             implementado
Wiring funcional                  pendiente de validar/completar
```

Este pendiente es funcional, no de infraestructura de red.

---

# 11. Estado actual por componente

```text
Frontend
[✓] desplegado
[✓] público
[✓] Nginx operativo

Backend
[✓] desplegado
[✓] SQLite persistente
[✓] acceso OCI operativo

Agentes
[✓] desplegado
[✓] indexación HTTP disponible
[✓] ChromaDB persistente
[✓] cache de embeddings persistente
[ ] LLM real pendiente

Data / IA
[✓] desplegado
[✓] health operativo
[✓] contrato /evaluate operativo
[✓] validación 422 operativa
[✓] 501 temporal esperado
[ ] evaluator real pendiente
```

---

# 12. Fuente de código actualmente desplegada

La VM está ejecutando actualmente la rama:

```text
infra/docker-backend
```

Esa rama contiene:

```text
QA integrado
+
cambios de Infra aún no promovidos
```

Por tanto, el entorno actual no debe interpretarse todavía como un despliegue oficial directo de `master`.

---

# 13. Principios de arquitectura actuales

```text
Internet → solo Frontend/Nginx
Backend  → orquestación y acceso a OCI
Agentes  → servicio interno
Data/IA  → servicio interno
SQLite   → volumen persistente
ChromaDB → volumen persistente
Secretos → fuera de Git y fuera de imágenes
```

La arquitectura distingue explícitamente entre:

```text
desplegado
≠
funcionalidad terminada
```

Esto permite integrar y validar infraestructura mientras algunos componentes funcionales del Sprint 2 continúan en desarrollo.
