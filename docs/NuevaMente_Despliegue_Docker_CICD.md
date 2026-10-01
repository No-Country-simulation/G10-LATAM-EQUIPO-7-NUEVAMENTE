# NuevaMente — Despliegue Docker y CI/CD

**Proyecto:** NuevaMente  
**Fecha de actualización:** 30 de septiembre de 2026  
**Objetivo:** documentar cómo se empaquetan, despliegan, operan y posteriormente automatizan los servicios de NuevaMente.

> Este documento no repite recursos OCI, IAM ni la arquitectura funcional completa.  
> Para esos temas consultar:
> - `NuevaMente_Infraestructura_OCI.md`
> - `NuevaMente_Arquitectura_OCI_Actual.md`

---

# 1. Modelo de despliegue actual

```text
Repositorio Git
→ Dockerfiles
→ Docker Compose
→ VM OCI
→ servicios en contenedores
```

Actualmente el despliegue es manual y utiliza `build:` desde el repositorio clonado en la VM.

CI/CD todavía no está implementado.

---

# 2. Servicios contenerizados

```text
frontend
backend
agents
data-ia
```

Estado:

| Servicio | Dockerizado | Compose |
|---|---|---|
| Frontend | Sí | Sí |
| Backend | Sí | Sí |
| Agentes | Sí | Sí |
| Data / IA | Sí | Sí |

---

# 3. Dockerfile — Frontend

Build multi-stage:

```text
Node 20 Alpine
→ npm ci
→ npm run build
→ dist/

Nginx Alpine
→ sirve dist/
→ proxy /api hacia Backend
```

Argumento de build utilizado:

```env
VITE_API_BASE_URL=/
```

Frontend no requiere volumen persistente.

---

# 4. Dockerfile — Backend

Base:

```text
python:3.11-slim
```

Proceso:

```text
pip install requirements.txt
→ copiar app
→ uvicorn app.main:app
```

Backend escucha internamente en `8000`.

Persistencia y credenciales se montan desde la VM; no se incluyen en la imagen.

---

# 5. Dockerfile — Agentes

Base:

```text
python:3.11-slim
```

Consideraciones especiales:

```text
libgomp1
PyTorch CPU
sentence-transformers
ChromaDB
pypdf
langchain-text-splitters
```

PyTorch se instala desde el índice CPU para evitar dependencias CUDA innecesarias.

Agentes escucha internamente en `8001`.

Persistencias externas:

```text
ChromaDB
cache Hugging Face
```

---

# 6. Dockerfile — Data / IA

Base:

```text
python:3.11-slim
```

Proceso:

```text
pip install requirements.txt
→ copiar data_ai
→ uvicorn data_ai.api.app:app
```

Data/IA escucha internamente en `8002`.

No requiere volumen persistente actualmente.

---

# 7. Docker Compose

Servicios actuales:

```text
backend
frontend
agents
data-ia
```

Publicación de puertos:

```text
frontend → 0.0.0.0:80:80
backend  → 127.0.0.1:8000:8000
agents   → 127.0.0.1:8001:8001
data-ia  → 127.0.0.1:8002:8002
```

La red por defecto de Compose permite resolución por nombre de servicio.

---

# 8. Variables y configuración de ejecución

Backend:

```env
ENVIRONMENT=staging
DEBUG=false
DATABASE_URL=sqlite:///storage/nuevamente.db

OCI_CONFIG_FILE=/run/oci/config
OCI_CONFIG_PROFILE=DEFAULT
OCI_NAMESPACE=axrhuqxl8oyi
OCI_BUCKET_NAME=bucket-nuevamente-2026
OCI_REGION=sa-bogota-1

RAG_BASE_URL=http://agents:8001
RAG_INDEX_PATH=/api/v1/index
RAG_TIMEOUT_SECONDS=120
```

Frontend:

```env
VITE_API_BASE_URL=/
```

Las claves privadas y `.env` productivos no se incluyen en las imágenes ni en Git.

---

# 9. Estructura actual en la VM

```text
/opt/nuevamente/
├── app/
│   └── repositorio Git clonado
├── compose/
├── env/
├── data/
│   ├── backend/
│   ├── agents/
│   └── huggingface/
└── secrets/
    └── oci/
        ├── config
        └── backend.pem
```

Directorio de trabajo habitual:

```text
/opt/nuevamente/app
```

---

# 10. Persistencia y secretos

| Uso | Host | Contenedor |
|---|---|---|
| SQLite | `/opt/nuevamente/data/backend` | `/app/storage` |
| ChromaDB | `/opt/nuevamente/data/agents` | `/app/chroma_db` |
| HF cache | `/opt/nuevamente/data/huggingface` | `/root/.cache/huggingface` |
| OCI config | `/opt/nuevamente/secrets/oci/config` | `/run/oci/config:ro` |
| OCI key | `/opt/nuevamente/secrets/oci/backend.pem` | `/run/oci/backend.pem:ro` |

Principio:

```text
imagen Docker = código + runtime + dependencias
volúmenes      = datos persistentes
secrets        = fuera de imagen y fuera de Git
```

---

# 11. Flujo de despliegue manual actual

```text
GitHub
→ git pull en la VM
→ docker compose build/up
→ validaciones HTTP
```

Comandos habituales:

```bash
cd /opt/nuevamente/app
git pull
docker compose up -d --build
```

Estado:

```bash
docker compose ps
```

Logs:

```bash
docker compose logs <servicio>
```

Recrear un servicio:

```bash
docker compose up -d --force-recreate <servicio>
```

---

# 12. Validaciones posteriores al despliegue

Frontend:

```text
GET / → 200
```

Backend:

```text
GET /api/v1/health → 200
```

Agentes:

```text
OpenAPI accesible
/index operativo
/generate operativo según estado funcional actual
```

Data / IA:

```text
GET /health                  → 200
POST /evaluate válido        → 501 esperado actualmente
POST /evaluate inválido      → 422
```

Persistencia:

```text
recrear Backend → SQLite permanece
recrear Agentes → ChromaDB permanece
```

---

# 13. Estrategia de ramas

```text
ramas de trabajo
      ↓
     QA
      ↓
   master
```

Uso esperado:

```text
QA
→ integración técnica y funcional
→ ejecución de CI

master
→ versión estable
→ fuente del despliegue oficial
```

La VM corre actualmente desde:

```text
infra/docker-backend
```

Esto es temporal durante la construcción y validación de Infra.

---

# 14. CI — Integración Continua

Objetivo:

```text
push / PR
→ instalar dependencias
→ ejecutar tests
→ validar builds
→ impedir integrar cambios rotos
```

Debe aplicarse al menos a:

```text
PR hacia QA
PR QA → master
```

Validaciones disponibles:

```text
Backend  → pytest + Ruff
Frontend → npm ci + npm run build
Agentes  → pytest
Data/IA  → pytest
```

Agentes requiere consideración especial por el peso de PyTorch/modelos de embeddings.

---

# 15. CD — Despliegue Continuo

Objetivo futuro:

```text
master
→ GitHub Actions
→ CI
→ build de imágenes Docker
→ GHCR
→ SSH a OCI
→ docker compose pull
→ docker compose up -d
→ healthchecks
```

La automatización debe construirse únicamente después de mantener estable el despliegue manual.

---

# 16. Registry y versionado de imágenes

Registry previsto:

```text
GHCR
```

Tags recomendados:

```text
sha-<commit>
```

Puede existir además un tag de conveniencia como `latest`, pero el despliegue debe poder identificar una imagen inmutable por commit.

Beneficios:

```text
trazabilidad
rollback
reproducibilidad
```

---

# 17. Evolución prevista de Compose con CI/CD

Hoy:

```yaml
build:
  context: ...
```

Objetivo futuro:

```yaml
image: ghcr.io/<org>/<servicio>:sha-<commit>
```

La VM dejará de compilar aplicaciones y pasará a descargar imágenes ya construidas y validadas.

---

# 18. Rollback

Con imágenes versionadas por SHA:

```text
despliegue nuevo falla
→ seleccionar tag anterior
→ docker compose pull
→ docker compose up -d
→ validar healthchecks
```

No será necesario recompilar para volver a una versión conocida.

---

# 19. Pendientes de automatización

```text
[ ] crear workflows GitHub Actions
[ ] CI en QA
[ ] CI en master
[ ] build de imágenes
[ ] publicación GHCR
[ ] secrets SSH en GitHub
[ ] CD desde master
[ ] healthchecks post-deploy
[ ] rollback probado
```

La contenerización y el despliegue manual de los cuatro servicios ya están resueltos; el siguiente objetivo de Infra es automatizar ese proceso sin alterar la arquitectura funcional de cada equipo.
