# NuevaMente

**Sistema Inteligente de Adaptación y Generación de Contenido Educativo**
Hackathon ONE · Grupo 10 · LATAM — Programa Oracle Next Education & Alura

---

## ¿Qué es NuevaMente?

NuevaMente es una plataforma que recibe documentación técnica (PDF, Markdown o texto plano) y la transforma automáticamente en material educativo personalizado según el perfil del destinatario, el nicho temático y el formato pedagógico elegido.

En lugar de que una persona tenga que adaptar manualmente un manual técnico denso para distintos públicos (alguien que recién empieza, un desarrollador semi-senior, un líder técnico, o un perfil no técnico), el sistema automatiza ese proceso combinando recuperación de información sobre el documento original con generación de contenido, y devuelve el material en alguno de estos formatos:

- Tutorial guiado paso a paso
- Flashcards de memorización
- Quiz interactivo con justificación de respuestas
- Resumen ejecutivo

El objetivo del proyecto es reducir el tiempo de producción de material didáctico de semanas a minutos, garantizando que el contenido generado se mantenga fiel a la fuente original.

## Módulos del sistema

El proyecto está dividido en módulos independientes, cada uno con su propia documentación detallada:

| Módulo | Responsabilidad | Documentación |
|---|---|---|
| **Frontend** | Interfaz de usuario: biblioteca de documentos, carga de archivos, centro de estudio (flashcards, quiz, tutorial, resumen) | [`frontend/README.md`](frontend/README.md) |
| **BackendAPI** | Recepción, validación, identificación y persistencia de documentos; frontera de integración hacia RAG | [`backend/README.md`](backend/README.md) |
| **RAG / Agentes** | Extracción, limpieza, segmentación (chunking), embeddings, búsqueda vectorial y orquestación de generación de contenido | rama `agentes/feature-rag` (nombre sujeto a cambios según avance el módulo) |
| **Data/IA** | Corpus de evaluación, Ground Truth, métricas de calidad de retrieval y validación del contenido generado | [`Data_IA/README.md`](Data_IA/README.md) |

Cada módulo se desarrolla en su propia rama y se integra a `QA` mediante Pull Requests una vez validado.

## Arquitectura general

```text
                ┌─────────────┐
   Usuario ───▶ │  Frontend   │
                └──────┬──────┘
                       │ HTTP (multipart / JSON)
                       ▼
                ┌─────────────┐
                │ BackendAPI  │  (validación, persistencia, estados)
                └──────┬──────┘
                       │ contrato interno de integración
                       ▼
                ┌─────────────┐
                │ RAG/Agentes │  (recuperación semántica + generación)
                └─────────────┘

  Data/IA evalúa offline la calidad del retrieval y del contenido
  generado, de forma independiente al flujo en producción.
```

Cada módulo se comunica con el siguiente a través de un contrato explícito y desacoplado (definido en cada README de módulo), de forma que ninguno depende de los detalles internos de implementación de otro.

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | HTML5, CSS3, JavaScript (ES6 Modules), sin frameworks |
| Backend | Python, FastAPI, Pydantic v2, SQLite |
| RAG / Agentes | Python, ChromaDB, sentence-transformers, LangChain (text splitters) |
| Evaluación (Data/IA) | Python, Pydantic, Jupyter Notebooks |
| Almacenamiento de archivos | Oracle Cloud Infrastructure (OCI) Object Storage — capa *Always Free* |

## Cómo correr el proyecto localmente

Cada módulo tiene sus propias instrucciones detalladas de instalación en su README correspondiente. En términos generales:

1. **Frontend**: se sirve como sitio estático (no requiere build). Incluye un modo demo sin conexión con datos de ejemplo, y un modo conectado al backend real. Ver [`frontend/README.md`](frontend/README.md).
2. **Backend**: entorno virtual de Python + `pip install -r requirements.txt`, se levanta con Uvicorn. Ver [`backend/README.md`](backend/README.md).
3. **RAG/Agentes**: entorno virtual de Python independiente, ver documentación de la rama correspondiente.
4. **Data/IA**: entorno virtual de Python independiente para notebooks y pruebas de evaluación. Ver [`Data_IA/README.md`](Data_IA/README.md).

Frontend y Backend pueden correrse juntos en local para probar la carga y persistencia de documentos de punta a punta. La generación de contenido adaptado todavía depende de que se conecte el módulo RAG/Agentes (ver estado del proyecto abajo); mientras tanto, el frontend permite probar toda la experiencia de usuario en modo demo con datos de ejemplo.

## Documentación adicional

En [`docs/`](docs) se encuentran diagramas de arquitectura, flujo funcional y lineamientos de trabajo en Git acordados por el equipo.

## Buenas prácticas de seguridad

- Nunca se commitean credenciales, tokens ni configuración sensible al repositorio; cada módulo usa un archivo `.env` local (ignorado por Git) a partir de su `.env.example`.
- El almacenamiento en la nube utiliza exclusivamente la capa *Always Free* de OCI.
- Los datos de ejemplo/evaluación versionados en el repositorio son de uso público o generados para el hackathon; no representan documentación confidencial de terceros.

## Estado del proyecto

Proyecto en desarrollo activo en el marco del Hackathon ONE (Sprint 1 en curso).

- **Frontend**: flujo completo de usuario implementado (biblioteca, carga, centro de estudio en sus 4 formatos), con modo demo y modo conectado al backend real.
- **BackendAPI**: recepción, validación, identificación y persistencia de documentos funcionando de punta a punta contra almacenamiento real; el endpoint de adaptación pedagógica está expuesto pero pendiente de conectarse al módulo RAG/Agentes.
- **RAG/Agentes**: en desarrollo.
- **Data/IA**: corpus de evaluación, Ground Truth y métricas de retrieval versionados y en uso para validar la calidad del pipeline a medida que avanza.

El estado detallado y actualizado de cada módulo se documenta en su propio README.
