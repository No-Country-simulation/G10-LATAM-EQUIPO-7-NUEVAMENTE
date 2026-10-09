# NuevaMente

**Sistema Inteligente de Adaptación y Generación de Contenido Educativo**  
Hackathon ONE · Grupo 10 · LATAM — Programa Oracle Next Education & Alura
Actualizacion 8 de octubre de 2026 _ Test2

---

## ¿Qué es NuevaMente?

NuevaMente es una plataforma que recibe documentación técnica en PDF, Markdown o texto plano y la transforma automáticamente en material educativo adaptado al perfil del destinatario, el contexto temático y el nivel de profundidad requerido.

El sistema combina recuperación aumentada por generación (RAG), búsqueda vectorial y generación asistida por modelos de lenguaje para trabajar siempre a partir del documento original.

El objetivo es reducir el tiempo necesario para convertir documentación técnica compleja en material de estudio, manteniendo dos principios centrales:

- **fidelidad a la fuente**, utilizando como contexto los fragmentos recuperados del documento original;
- **adaptación pedagógica**, ajustando lenguaje, profundidad y presentación al perfil solicitado.

El alcance funcional de **Sprint 2** se concentra en dos formatos educativos:

- **Quiz interactivo**, con opciones, respuesta correcta y justificación;
- **Flashcards**, con concepto o pregunta y su correspondiente explicación.

Otros formatos contemplados por el producto, como tutoriales y resúmenes, forman parte de iteraciones posteriores.

---

## Módulos del sistema

NuevaMente está dividido en servicios desacoplados que se comunican mediante contratos explícitos.

| Módulo | Responsabilidad | Documentación |
|---|---|---|
| **Frontend** | Interfaz de usuario, carga de documentos, biblioteca y visualización de Quiz y Flashcards | [`frontend/README.md`](frontend/README.md) |
| **BackendAPI** | Orquestación del producto, validación, persistencia, estados, OCI e integración con RAG/Agentes | [`backend/README.md`](backend/README.md) |
| **RAG / Agentes** | Extracción, chunking, embeddings, búsqueda vectorial, recuperación por documento y generación educativa | [`agentes/README.md`](agentes/README.md) |
| **Data/IA** | Ground Truth, métricas de retrieval, contratos de evaluación y evaluación de calidad del contenido generado | [`Data_IA/README.md`](Data_IA/README.md) |
| **Infraestructura** | Contenerización, despliegue en OCI, red, persistencia y preparación de CI/CD | [`docs/`](docs) |

Los cambios desarrollados en ramas de trabajo se integran mediante Pull Requests hacia `QA`, donde se realiza la validación conjunta antes de promover una versión estable.

---

## Arquitectura general

```text
                     ┌──────────────┐
                     │   Usuario    │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Frontend   │
                     └──────┬───────┘
                            │ HTTP
                            ▼
                 ┌──────────────────────┐
                 │      BackendAPI      │
                 │                      │
                 │ orquestación         │
                 │ estados              │
                 │ persistencia         │
                 └──────┬─────────┬─────┘
                        │         │
             documentos │         │ indexación /
             y metadata │         │ generación
                        ▼         ▼
                ┌────────────┐  ┌──────────────┐
                │ OCI Object │  │ RAG / Agentes│
                │  Storage   │  │              │
                └────────────┘  │ extracción   │
                                │ chunking      │
                                │ embeddings    │
                                │ retrieval     │
                                │ generación    │
                                └──────┬───────┘
                                       │
                                       │ contenido generado
                                       │ + chunks utilizados
                                       ▼
                                ┌──────────────┐
                                │   Data / IA  │
                                │              │
                                │ evaluación   │
                                │ de calidad   │
                                └──────────────┘
```

BackendAPI funciona como **orquestador central del producto**.

Frontend no accede directamente a OCI, al Vector Store ni a los servicios de Agentes. Backend mantiene el control del flujo y utiliza contratos HTTP desacoplados para comunicarse con los demás componentes.

La integración de Data/IA con el flujo productivo completo no forma parte obligatoria del E2E de Sprint 2; durante este Sprint se dejó preparado su servicio de evaluación y los contratos necesarios para incorporarlo posteriormente al pipeline.

---
## RAG y generación educativa

El módulo RAG / Agentes procesa documentos reales mediante:

```text
extracción
→ limpieza
→ chunking
→ embeddings
→ almacenamiento vectorial
→ retrieval
→ generación educativa
```

La recuperación está filtrada por `document_id`, evitando mezclar información perteneciente a documentos distintos.

Para cada generación se conservan también los chunks utilizados como evidencia.
Esto permite mantener trazabilidad entre el contenido generado y las fuentes recuperadas.
El servicio de generación recibe el contexto pedagógico solicitado y produce salidas estructuradas para Quiz y Flashcards.

---

## Evaluación — Data/IA

Data/IA trabaja en dos tipos de evaluación diferentes.

### Evaluación de retrieval

Utiliza un corpus controlado y Ground Truth versionado para medir la capacidad del RAG de recuperar evidencia relevante.

Métricas utilizadas:

```text
Recall@K
Precision@K
```

Actualmente existen versiones congeladas del Ground Truth que permiten comparar resultados de forma reproducible.

El servicio valida primero los contratos estructurales y posteriormente aplica una evaluación de calidad.

Durante Sprint 2 se implementó un **baseline heurístico reproducible**, acompañado de una rúbrica de decisión y resultados estructurados.

Estados posibles de evaluación:

```text
aprobado
requiere_revision
rechazado
```

La evolución hacia evaluación semántica más avanzada y un Agente Revisor forma parte de las siguientes iteraciones del proyecto.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | HTML5, CSS3, JavaScript ES6, Vite |
| Backend | Python, FastAPI, Pydantic v2, SQLite, HTTPX |
| RAG / Agentes | Python, FastAPI, ChromaDB, sentence-transformers, LangChain Text Splitters |
| Data/IA | Python, FastAPI, Pydantic, Pytest, Jupyter Notebooks |
| Archivos | Oracle Cloud Infrastructure Object Storage |
| Infraestructura | OCI Compute, Docker, Docker Compose, Nginx |
| Persistencia vectorial | ChromaDB |
| Persistencia de negocio | SQLite |

---

## Infraestructura y despliegue

El despliegue actual utiliza Docker Compose sobre una máquina virtual OCI.

```text
GitHub
   ↓
repositorio en VM
   ↓
Docker Compose
   ├── Frontend
   ├── Backend
   ├── Agentes
   └── Data/IA
```

Frontend es servido mediante Nginx y utiliza el Backend como única puerta de entrada al producto.

Los servicios internos de Backend, Agentes y Data/IA no necesitan exponerse directamente al usuario.

La infraestructura mantiene persistencia externa para:

```text
SQLite
ChromaDB
cache de modelos
```

Las credenciales y claves de OCI permanecen fuera de las imágenes Docker y fuera del repositorio.

El despliegue se realiza actualmente de forma manual. La automatización mediante CI/CD y publicación de imágenes versionadas forma parte de la siguiente etapa de Infraestructura.

Más información:

- [`docs/NuevaMente_Infraestructura_OCI.md`](docs/NuevaMente_Infraestructura_OCI.md)
- [`docs/NuevaMente_Despliegue_Docker_CICD.md`](docs/NuevaMente_Despliegue_Docker_CICD.md)

---
## Documentación adicional

La carpeta [`docs/`](docs) contiene documentación complementaria sobre:

- arquitectura;
- infraestructura OCI;
- Docker y despliegue;
- integración de servicios;
- flujo funcional del producto;
- lineamientos técnicos del equipo.

Cada módulo mantiene además su documentación específica en su propio README.

---

## Buenas prácticas de seguridad

- No se versionan credenciales, tokens, claves privadas ni secretos.
- Los archivos `.env` de ejecución permanecen fuera de Git.
- Las configuraciones públicas se documentan mediante `.env.example`.
- OCI Object Storage utiliza un bucket privado.
- El acceso desde Backend utiliza identidad técnica y API Signing Keys.
- Las claves privadas permanecen fuera del repositorio y de las imágenes Docker.
- Los servicios internos no se exponen públicamente cuando no es necesario.
- Los datos utilizados para evaluación son públicos o preparados específicamente para el hackathon.

---
