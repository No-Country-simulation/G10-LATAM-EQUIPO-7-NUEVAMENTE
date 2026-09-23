NuevaMente - Agentes
Agent V1 + RAG Core

Módulo de Ingestión y Recuperación de Conocimiento
La responsabilidad de esta rama es construir la base de conocimiento del agente V1, encargada de:

Extraer información de documentos.
Limpiar y normalizar el contenido.
Dividir el contenido en chunks.
Generar embeddings multilingües.
Almacenar los embeddings en un Vector Store.
Recuperar información relevante mediante consultas.
Proporcionar una interfaz desacoplada para que el agente pueda consumir el conocimiento.
COMPONENTES

agent/agent_v1.py
Contiene la estructura inicial del agente.

Su responsabilidad es coordinar el acceso al conocimiento.

utiliza servicios retriever.retrieve(...) ||| Esto permite mantener el agente desacoplado de la implementación interna del RAG. |||

rag/models.py
Contiene los modelos de datos utilizados por el módulo.

El objetivo es mantener estructuras comunes entre los diferentes componentes.

rag/extractor.py
Responsable de extraer el contenido de: .pdf .md .txt

Cada página se trata como una unidad documental inicial.

Ejemplo:

manual.pdf ↓ Página 1 Página 2 Página 3 ...

Cada página conserva metadata:

{ "source": "manual.pdf", "page": 3, "file_type": "pdf" }

Esto permite mantener trazabilidad durante las etapas posteriores.

rag/cleaner.py
Responsable de normalizar el texto.

Entre las operaciones realizadas: Normalización Unicode ↓ Normalización de saltos de línea ↓ Eliminación de espacios innecesarios ↓ Texto limpio

La limpieza debe intentar reducir ruido sin eliminar información importante.

rag/chunker.py
Divide el texto en fragmentos pequeños.

Cada chunk mantiene la información del documento del que proviene.

Ejemplo:

{ "chunk_id": "manual_3_2", "source": "manual.pdf", "page": 3, "chunk_index": 2 }

rag/embeddings.py
Convierte el contenido textual en vectores numéricos.

Texto ↓ Embedding Model ↓ Vector

La implementación utiliza embeddings multilingües para permitir que el sistema trabaje con contenido y consultas en distintos idiomas.

rag/vector_store.py
Se encarga de almacenar:

Chunks Embeddings Metadata

y posteriormente realizar búsquedas semánticas.

Actualmente el Vector Store utilizado es:

ChromaDB

El resto del sistema no debería depender directamente de ChromaDB.

Por ejemplo:

vector_store.search( query="¿Qué es una VCN?", top_k=5 )

rag/retriever.py
Este componente proporciona la interfaz principal de recuperación.

Ejemplo:

results = retriever.retrieve( query="¿Qué es una VCN?", top_k=5 )

Devuelve:

[
      SearchResult(
         chunk_id="manual_12_3",
         text="Una VCN es...",
         score=0.91,
         metadata={
            "source": "manual.pdf",
            "page": 12
         }
       }   
 }
El agente utiliza este componente para obtener el contexto relevante.

rag/pipeline.py
Coordina el flujo completo de ingestión.

Archivo ↓ Extractor ↓ Cleaner ↓ Chunker ↓ Embedding ↓ Vector Store

api/files.py
Este módulo contiene la funcionalidad relacionada con la recuperación de archivos mediante API.

La idea es desacoplar el agente del proveedor de almacenamiento.

Arquitectura:

Agent ↓ File Provider ↓ API ↓ Archivo

El agente no necesita conocer directamente cómo funciona la API.

Flujo de recuperación
Pregunta ↓ Retriever ↓ Embedding de consulta ↓ Vector Store ↓ Top K resultados ↓ Score + Metadata ↓ Agent V1