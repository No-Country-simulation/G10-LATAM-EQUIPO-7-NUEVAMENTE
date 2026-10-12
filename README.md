# NuevaMente

**Sistema Inteligente de Adaptación y Generación de Contenido Educativo**  
Hackathon ONE · Grupo 10 · LATAM — Programa Oracle Next Education & Alura

---

## ¿Qué es NuevaMente?

NuevaMente es una plataforma que recibe documentación técnica en PDF, Markdown o texto plano y la transforma automáticamente en material educativo adaptado al perfil del destinatario, el contexto temático y el nivel de profundidad requerido.

El sistema combina recuperación aumentada por generación (RAG), búsqueda vectorial y generación asistida por modelos de lenguaje para trabajar siempre a partir del documento original.

El objetivo es reducir el tiempo necesario para convertir documentación técnica compleja en material de estudio, manteniendo dos principios centrales:

- **fidelidad a la fuente**, utilizando como contexto los fragmentos recuperados del documento original;
- **adaptación pedagógica**, ajustando lenguaje, profundidad y presentación al perfil solicitado.

El producto genera y presenta cuatro formatos educativos:

- **Quiz interactivo**, con opciones, respuesta correcta y justificación;
- **Flashcards**, con concepto o pregunta y su correspondiente explicación;
- **Resumen ejecutivo** (`tldr`), con síntesis, puntos clave y conclusión;
- **Guion de video** (`video_script`), organizado en escenas con narración y descripción visual.

El material se adapta al perfil, nicho temático, nivel de detalle y objetivo de aprendizaje definidos para cada documento.

---

## Módulos del sistema

NuevaMente está dividido en servicios desacoplados que se comunican mediante contratos explícitos.

| Módulo | Responsabilidad | Documentación |
|---|---|---|
| **Frontend** | Interfaz para cargar documentos, consultar la biblioteca y estudiar los formatos generados | [`frontend/README.md`](frontend/README.md) |
| **BackendAPI** | Punto de entrada HTTP y orquestador del ciclo de vida documental, la generación y la evaluación | [`backend/README.md`](backend/README.md) |
| **Agentes** | Indexación RAG, recuperación de evidencia y generación de contenido | [`agentes/README.md`](agentes/README.md) |
| **Data/IA** | Evaluación de contenido generado, rúbricas y herramientas de evaluación de retrieval | [`Data_IA/README.md`](Data_IA/README.md) |
| **Infraestructura** | Contenedores, despliegue y recursos OCI | [`docs/`](docs) |

Cada módulo documenta por separado su arquitectura, contratos y operación. Este README resume cómo colaboran para entregar el producto.

## Navegación

| Si buscas… | Consulta… |
|---|---|
| El recorrido de un documento y sus estados | [Arquitectura y flujo del producto](#arquitectura-y-flujo-del-producto) |
| Tecnologías principales | [Stack tecnológico](#stack-tecnológico) |
| Despliegue y documentación de infraestructura | [Infraestructura y despliegue](#infraestructura-y-despliegue) y [Documentación adicional](#documentación-adicional) |
| Detalles de implementación de un servicio | README de [Frontend](frontend/README.md), [BackendAPI](backend/README.md), [Agentes](agentes/README.md) o [Data/IA](Data_IA/README.md) |
| Prácticas transversales de seguridad | [Buenas prácticas de seguridad](#buenas-prácticas-de-seguridad) |

---

## Arquitectura y flujo del producto

```text
 Usuario
   │
   ▼
Frontend ──HTTP──> BackendAPI ──> SQLite: metadata, estados, formatos y evaluaciones
                       │   │
                       │   ├────> OCI Object Storage: documento original y paquete educativo
                       │   │
                       │   ├────> Agentes ──> ChromaDB: chunks indexados por documento
                       │   │         └──────> Gemini: generación estructurada
                       │   │
                       │   └────> Data/IA: evaluación de formatos generados
                       │
                       └── responde al Frontend; este consulta estados y resultados
```

BackendAPI es el **orquestador central** y el único intermediario entre el Frontend y los servicios de procesamiento. Mantiene la metadata y los estados en SQLite; almacena el original y el paquete educativo vigente en OCI Object Storage; y coordina Agentes y Data/IA mediante sus adaptadores HTTP.

### Recorrido de un documento

1. El usuario carga un PDF, Markdown o TXT y define el perfil, nicho, nivel de detalle y, opcionalmente, un objetivo de aprendizaje.
2. Backend valida el archivo, asigna una identidad al documento, guarda el original y solicita su indexación. El documento queda disponible para procesamiento cuando la indexación termina correctamente.
3. Backend registra los cuatro formatos como `processing` y responde al Frontend. La generación continúa en segundo plano; el Frontend consulta los estados y resultados a través de Backend.
4. Agentes recupera fragmentos del documento indexado y genera Quiz, Flashcards, resumen y guion de video. Los resultados incluyen metadata pedagógica y evidencia (`chunks_used`) para mantener la trazabilidad.
5. Backend persiste los formatos y la metadata pedagógica, actualiza el paquete educativo en Object Storage y solicita a Data/IA evaluar cada formato generado que está listo para evaluación. Los resultados de evaluación se guardan como historial separado del contenido.

Los errores de generación y evaluación se registran por separado: un problema en la evaluación no convierte por sí solo un formato ya generado correctamente en un fallo de generación. La evaluación de calidad de formatos está integrada en el flujo de Backend; el benchmark de retrieval con corpus versionado también puede ejecutarse de forma independiente. El alcance técnico y los contratos de esos procesos están en los README de [Backend](backend/README.md), [Agentes](agentes/README.md) y [Data/IA](Data_IA/README.md).

### Estado observable

El documento y cada formato tienen ciclos de estado distintos. La indexación debe concluir antes de comenzar la generación; los formatos pasan de `processing` a `success`, `failed` o `no_results`. La biblioteca puede mostrar resultados parciales mientras se completan los demás formatos. La evaluación tiene su propio resultado —`aprobado`, `requiere_revision` o `rechazado`— y no sustituye el estado de generación.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | HTML5, CSS3, JavaScript ES6, Vite |
| Backend | Python, FastAPI, Pydantic v2, SQLite, HTTPX |
| Agentes / RAG | Python, FastAPI, Gemini (`google-genai`), ChromaDB, BM25, Cross-Encoder, sentence-transformers |
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
