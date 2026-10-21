# Planning Sprint 2 — NuevaMente

**Proyecto:** NuevaMente — Sistema Inteligente de Adaptación y Generación de Contenido Educativo  
**Sprint:** 2  
**Fecha de planning:** 28 de septiembre de 2026  
**Documento:** Informe de acuerdos, arquitectura, alcance y tareas del Sprint 2

---

## 1. Objetivo general del Sprint 2

Sprint 1 permitió construir las piezas principales del sistema de manera relativamente independiente: carga de documentos, almacenamiento en OCI, Backend API, pipeline RAG, evaluación de retrieval, Frontend e infraestructura inicial.

El objetivo de Sprint 2 es comenzar a convertir esas piezas en **un producto integrado y funcional**, priorizando el flujo completo del documento desde su carga hasta la generación, persistencia y visualización de contenido educativo.

El resultado esperado del Sprint es disponer de un flujo funcional que permita:

1. cargar un documento desde Frontend;
2. almacenarlo y persistir su información mediante Backend;
3. indexarlo mediante Agentes/RAG;
4. generar automáticamente los formatos definidos para este Sprint;
5. persistir dichos formatos;
6. consultar los documentos existentes desde la biblioteca;
7. abrir un documento y visualizar los formatos generados;
8. dejar preparado el servicio de evaluación de Data/IA para integración posterior.

---

# 2. Decisiones principales del planning

## 2.1 Formatos incluidos en Sprint 2

Para este Sprint se trabajará únicamente con dos formatos:

- **Quiz**
- **Flashcards**

Aunque la arquitectura debe mantenerse extensible para incorporar otros formatos en iteraciones posteriores, el alcance funcional actual se concentra en estos dos.

---

## 2.2 Generación automática de formatos

La experiencia de producto definida para la aplicación será:

```text
Documento cargado
→ procesamiento / indexación
→ generación automática de Quiz + Flashcards
→ persistencia de ambos formatos
→ disponibilidad en la biblioteca
```

El usuario no tendrá que solicitar manualmente cada formato desde la interfaz actual.

Sin embargo, se acordó preservar una arquitectura capaz de soportar la **generación individual de un formato**, de manera que el sistema no quede acoplado exclusivamente a la experiencia visual actual.

Conceptualmente, la capacidad base debe poder representar:

```text
documento + formato + parámetros
→ una adaptación
```

La aplicación de Sprint 2 utilizará esa capacidad para solicitar automáticamente los dos formatos definidos.

---

# 3. Principio arquitectónico principal

## Backend API como orquestador del producto

Backend API será responsable de coordinar el flujo general de la aplicación.

Backend es el componente que se comunica con:

- Frontend;
- OCI Object Storage;
- Base de Datos;
- Agentes / RAG.

Backend es además el único componente que debe acceder directamente a **OCI** y a la **base de datos de negocio**.

```text
Frontend
    ↓
Backend API
   ├── OCI Object Storage
   ├── Base de Datos
   └── Agentes / RAG
```

Agentes no debe acceder directamente a OCI ni a la base de datos de negocio.

---

# 4. Flujo principal de procesamiento del documento

El flujo acordado para Sprint 2 es el siguiente:

```text
Frontend
→ Backend recibe documento
→ Backend guarda documento original en OCI
→ Backend persiste metadata / estado en BD
→ Backend solicita indexación a Agentes
→ Agentes indexa el documento
→ Agentes confirma indexación
→ Backend solicita generación de Quiz + Flashcards
→ Agentes genera los formatos
→ Agentes devuelve resultados a Backend
→ Backend persiste los formatos
→ documento queda disponible para consulta
```

Una decisión importante del planning es que **indexación y generación son operaciones separadas**.

La finalización del RAG no debe disparar automáticamente la generación desde Agentes.

Agentes:

```text
indexa
→ confirma que terminó
→ espera una nueva solicitud
```

Backend:

```text
recibe confirmación
→ decide cuándo solicitar generación
```

Esto mantiene el control de la orquestación del producto en Backend.

---

# 5. Contrato Backend → Agentes para indexación

Durante la indexación, Backend debe enviar el documento a Agentes.

Conceptualmente el contrato debe contener información equivalente a:

```json
{
  "document_id": "...",
  "filename": "...",
  "mime_type": "...",
  "content": "..."
}
```

El contenido/bytes del archivo se envían **únicamente en esta etapa**.

Agentes realiza:

```text
extracción
→ limpieza
→ chunking
→ embeddings
→ almacenamiento en Vector Store
```

Los chunks son fragmentos del documento; el conjunto de chunks asociados al mismo `document_id` representa el documento indexado dentro del pipeline RAG.

La respuesta de indexación debe confirmar al menos el documento procesado y su estado, conceptualmente:

```json
{
  "document_id": "...",
  "status": "indexed"
}
```

Una vez indexado, las operaciones posteriores no deberían requerir nuevamente el archivo completo.

---

# 6. Generación de formatos en Agentes

Después de la indexación, Backend realiza una nueva llamada solicitando los formatos que necesita.

Para Sprint 2:

```json
{
  "document_id": "...",
  "formats": ["quiz", "flashcards"],
  "profile": "...",
  "niche": "...",
  "detail_level": "..."
}
```

Los nombres definitivos de los campos corresponden al contrato técnico que Backend y Agentes acuerden internamente.

La idea arquitectónica es mantener una **capacidad atómica de generación** dentro de Agentes:

```text
generate_format(document_id, formato, parámetros)
→ genera UN formato
```

El endpoint puede recibir uno o varios formatos:

```text
Endpoint recibe N formatos
        ↓
por cada formato solicitado
        ↓
capacidad atómica genera UNO
```

Esto permite que la aplicación actual solicite Quiz + Flashcards, pero que un consumidor externo pueda solicitar solo uno de ellos.

---

# 7. Respuesta Agentes → Backend

Agentes deberá devolver a Backend los formatos generados.

El contrato final debe ser acordado por ambos equipos, pero conceptualmente puede representar:

```json
{
  "document_id": "...",
  "results": [
    {
      "format": "quiz",
      "status": "success",
      "content": {}
    },
    {
      "format": "flashcards",
      "status": "success",
      "content": {}
    }
  ]
}
```

Agentes **no persiste directamente los formatos en la base de datos de negocio**.

La responsabilidad queda así:

```text
Agentes
→ genera
→ devuelve

Backend
→ recibe
→ persiste
```

---

# 8. Persistencia y modelo de datos

Se identificó durante el planning que no era suficiente tener tareas como "persistir documento" o "persistir formatos" sin definir previamente el modelo de datos.

Por ello se agregó una tarea específica para diseñar el modelo de BD para:

- documentos;
- formatos generados;
- evaluaciones;
- relaciones entre dichas entidades.

Como referencia conceptual podrían existir entidades equivalentes a:

```text
document
    1
    |
    N
document_format
    1
    |
    N
format_evaluation
```

La estructura final será definida por Backend/Data IA durante la implementación.

También se planteó considerar estados del documento como:

```text
UPLOADED
PROCESSING
PARTIAL
READY
ERROR
```

Estos nombres no se fijaron como contrato definitivo; son una referencia para que el equipo cierre el modelo de estados.

---

# 9. Manejo parcial de formatos

Se dejó como directriz funcional que los formatos puedan manejarse de forma independiente.

Si un formato se genera correctamente y otro falla:

- el formato exitoso debe conservarse;
- no debería ser necesario regenerarlo;
- el documento puede quedar en un estado parcial;
- debe ser posible reintentar únicamente el formato fallido.

La implementación concreta —estados, estrategia de reintentos y manejo de excepciones— queda a criterio del equipo técnico.

---

# 10. Flujo de consulta desde la biblioteca

La consulta y la generación son flujos separados.

Una vez que existen documentos persistidos, Frontend consume la información exclusivamente mediante Backend.

## 10.1 Biblioteca

```text
Frontend
→ GET /documents
→ Backend consulta BD
→ devuelve documentos disponibles
→ Frontend construye biblioteca
```

## 10.2 Detalle de documento

```text
Frontend
→ GET /documents/{id}
→ Backend consulta metadata
→ Frontend muestra detalle
```

Metadata esperada a nivel conceptual:

- `id`;
- título;
- nombre corto;
- resumen;
- tiempo estimado;
- estado;
- otros metadatos definidos por el equipo.

## 10.3 Formatos generados

Se dejó una operación específica para consultar formatos por documento:

```text
GET /documents/{id}/formats
```

Backend devuelve los formatos disponibles para ese `document_id`.

En Sprint 2:

```text
Quiz
Flashcards
```

Frontend no consulta directamente:

- OCI;
- Base de Datos;
- Agentes.

Toda consulta pasa por Backend API.

---

# 11. Data / IA — alcance de Sprint 2

Data/IA trabajará sobre la **evaluación de calidad del contenido generado**.

En este Sprint debe dejar preparado un servicio que permita evaluar un formato generado a partir de información equivalente a:

```json
{
  "document_id": "...",
  "format": "quiz",
  "generated_content": {},
  "chunks_used": []
}
```

## 11.1 Criterios de evaluación

Las políticas de calidad planteadas para este Sprint incluyen:

- relevancia;
- coherencia;
- adaptación didáctica;
- información respaldada por los chunks utilizados.

Data/IA debe:

```text
validar contrato JSON
→ evaluar salida generada
→ producir evaluación estructurada
→ retornar resultados / observaciones
```

---

# 12. Diferencia entre evaluación de retrieval y evaluación del formato

Se aclaró que no deben mezclarse ambos tipos de evaluación.

## Evaluación de retrieval

Trabajada desde Sprint 1:

```text
Ground Truth
→ retrieval
→ comparación con evidencia esperada
→ Recall@K / Precision@K
```

Estas métricas requieren un ground truth y pertenecen a otro flujo de evaluación.

## Evaluación del contenido generado

Sprint 2:

```text
chunks_used
+ generated_content
→ evaluación de calidad
```

Se concentra en:

- relevancia;
- coherencia;
- adaptación didáctica;
- respaldo en la fuente.

Por ello no se deben presentar Recall@K o Precision@K como métricas derivadas directamente de este endpoint de evaluación de formatos.

---

# 13. Integración Agentes ↔ Data / IA

La integración completa no es obligatoria en Sprint 2.

Durante este Sprint:

### Agentes

Debe quedar en capacidad de identificar los `chunks_used` utilizados durante la generación.

### Data / IA

Debe:

- definir y validar contratos JSON;
- implementar la evaluación;
- retornar una respuesta estructurada;
- exponer el endpoint de evaluación.

Conceptualmente, una futura integración podrá seguir el flujo:

```text
Agentes
→ generated_content + chunks_used
→ Data / IA
→ evaluación
```

La conexión efectiva entre servicios puede realizarse posteriormente si no entra dentro del tiempo disponible del Sprint.

---

# 14. Responsabilidades por componente

## Frontend

Responsabilidades principales del Sprint:

- ajustar flujo real después de `POST /documents`;
- corregir documentación/adaptations;
- eliminar dependencia de URL de Backend hardcodeada / validar configuración mediante Vite;
- validar tamaño máximo de archivo de 10 MB;
- manejar errores en UI/UX;
- solicitar y mostrar los documentos existentes;
- solicitar formatos del documento abierto;
- presentar Quiz y Flashcards.

---

## Backend API

Responsabilidades principales:

- comunicarse con OCI;
- persistir documentos, metadata, estados y formatos;
- diseñar el modelo de datos;
- enviar el documento a Agentes para indexación;
- orquestar la generación de Quiz y Flashcards;
- recibir resultados desde Agentes;
- persistir formatos;
- exponer consultas de biblioteca, metadata y formatos;
- mantener la coordinación general del producto.

---

## Agentes / RAG

Responsabilidades principales:

- endpoint de indexación;
- extracción y procesamiento RAG;
- filtro de retrieval por `document_id`;
- generación de Quiz y Flashcards;
- integración con LLM;
- Prompt Engineering;
- capacidad atómica de generación por formato;
- recuperación de `top-k` chunks utilizados;
- contrato de respuesta de formatos hacia Backend.

Agentes no accede directamente a OCI ni a la BD de negocio.

---

## Data / IA

Responsabilidades principales:

- validar contratos JSON de formatos;
- definir políticas de calidad;
- implementar evaluación del JSON;
- retornar información de evaluación;
- exponer endpoint de evaluación.

La integración con el pipeline no es obligatoria para cerrar Sprint 2.

---

## Infraestructura

Responsabilidades principales:

- instalar Python, MySQL y Nginx;
- desplegar entornos de Frontend, Backend, Agentes y Data/IA;
- disponer URLs públicas mediante Nginx;
- preparar CI/CD desde GitHub.

---

## QA

Responsabilidades principales:

### Integración Frontend + Backend

Validar la comunicación real entre ambos componentes.

### Prueba end-to-end del flujo de generación

```text
cargar documento
→ persistencia
→ Backend envía a Agentes
→ indexación
→ Backend solicita Quiz + Flashcards
→ retrieval por document_id
→ generación Quiz + Flashcards
→ Backend recibe resultados
→ persistencia
→ recuperación desde Backend
→ visualización en Frontend
```

La evaluación Data/IA no es requisito obligatorio de este E2E en Sprint 2.

---

# 15. Contratos críticos del Sprint

No todos los detalles técnicos deben definirse desde Project Management. Sin embargo, existen contratos que deben cerrarse entre áreas porque son dependencias directas.

## 15.1 Backend ↔ Agentes — Indexación

Debe quedar definido:

- estructura de entrada;
- cómo viaja el archivo;
- `document_id` común;
- tipos de archivo/MIME;
- respuesta de indexación;
- significado de `indexed`.

---

## 15.2 Backend ↔ Agentes — Generación

Debe quedar definido:

- `document_id`;
- lista de formatos solicitados;
- parámetros de adaptación;
- estructura de resultados;
- comportamiento ante generación parcial.

---

## 15.3 Backend ↔ Frontend — Consulta

Debe quedar definido:

- contrato de `GET /documents`;
- contrato de `GET /documents/{id}`;
- contrato de `GET /documents/{id}/formats`;
- representación de estados;
- estructura de errores amigables.

---

## 15.4 Agentes ↔ Data / IA — Contrato preparado

Aunque la integración no sea obligatoria durante el Sprint, debe quedar claro qué información podrá viajar posteriormente:

```text
document_id
format
generated_content
chunks_used
```

---

# 16. Puntos críticos y riesgos identificados

## Integración tardía

Sprint 1 mostró que dejar las integraciones para el final reduce el margen de QA y corrección.

Durante Sprint 2 se debe integrar progresivamente.

---

## Dependencia del `document_id`

El mismo identificador debe mantenerse de forma coherente entre:

```text
Backend
→ BD
→ Agentes
→ Vector Store
→ formatos
```

Una inconsistencia en este identificador afectaría retrieval, generación y consultas posteriores.

---

## Acoplamiento de Agentes a infraestructura de negocio

Se debe evitar que Agentes comience a consultar directamente OCI o la base de datos de negocio.

Backend mantiene esa responsabilidad.

---

## Trabajo duplicado

Cuando más de una persona participe en el mismo componente, se deben acordar responsables y alcance antes de implementar soluciones equivalentes en paralelo.

---

## Contratos incompatibles

Backend, Frontend, Agentes y Data/IA pueden desarrollar en paralelo, pero deben mantener contratos compatibles.

Project Management hará seguimiento a estas dependencias sin sustituir las decisiones técnicas internas del equipo.

---

# 17. Decisiones deliberadamente dejadas al equipo técnico

El planning no pretende definir cada detalle de implementación.

Quedan a criterio de los responsables técnicos, entre otros:

- nombres definitivos de campos JSON;
- estructura final de tablas;
- implementación del modelo de estados;
- política de reintentos;
- manejo de timeouts;
- códigos de error;
- estructura interna de servicios;
- librerías y patrones concretos;
- mecanismos de resiliencia;
- detalles de implementación de la capacidad atómica.

La intervención de PM/arquitectura se concentrará en aquellos casos donde una decisión:

- afecte varias áreas;
- cambie el comportamiento del producto;
- rompa un contrato;
- genere una dependencia crítica;
- bloquee el cumplimiento del Sprint.

---

# 18. Material visual de referencia

Durante el planning se prepararon cuatro gráficos para condensar los acuerdos:

### A. Arquitectura y responsabilidades

Mapa de componentes, fronteras y responsabilidades.

### B. Flujo de procesamiento del documento

Recorrido desde carga hasta generación y persistencia de Quiz + Flashcards.

### C. Flujo de consulta desde la biblioteca

Consulta de documentos, metadata y formatos persistidos desde Frontend mediante Backend.

### D. Servicio de evaluación Data / IA

Alcance real de Data/IA durante Sprint 2 y preparación del contrato para futura integración.

Estos diagramas funcionan como referencia compartida del Sprint y no como una especificación rígida de implementación.

---

# 19. Comunicación y coordinación del equipo

Las tareas del Sprint están organizadas en Trello por área.

Los integrantes que no participaron directamente en el planning deben revisar:

- los gráficos compartidos en el canal `#software-engineer`;
- las tareas correspondientes en Trello;
- los acuerdos de arquitectura y fronteras descritos en este documento.

Si una persona no tiene claro qué tarea abordar, debe coordinarse primero con su área para evitar trabajo duplicado o implementaciones incompatibles.

Bloqueos, dependencias o decisiones que afecten varias áreas deben comunicarse lo antes posible.

---

# 20. Definición general de éxito del Sprint 2

Sprint 2 puede considerarse exitoso cuando el sistema sea capaz de demostrar de forma integrada:

```text
Documento
→ carga
→ almacenamiento
→ persistencia
→ indexación
→ generación Quiz + Flashcards
→ persistencia de resultados
→ consulta desde biblioteca
→ visualización en Frontend
```

Además:

- Backend debe mantener la orquestación del producto;
- Agentes debe mantener el procesamiento de IA desacoplado de OCI/BD;
- Data/IA debe dejar operativo su servicio de evaluación, aunque todavía no esté integrado al flujo productivo;
- Infraestructura debe facilitar un entorno compartido de integración;
- QA debe validar el recorrido end-to-end.

---

# Conclusión

El foco de Sprint 2 no es añadir gran cantidad de funcionalidades nuevas, sino **integrar correctamente las capacidades ya construidas y cerrar el flujo principal del producto**.

La dirección acordada puede resumirse así:

> **Backend orquesta el producto; Agentes ejecuta el pipeline de IA; Data/IA prepara la evaluación; Frontend consume el producto a través de Backend; OCI y la base de datos permanecen bajo responsabilidad de Backend.**

El Sprint debe priorizar contratos claros, integración incremental y comunicación temprana de dependencias, manteniendo libertad técnica dentro de cada área para decidir la implementación concreta.
