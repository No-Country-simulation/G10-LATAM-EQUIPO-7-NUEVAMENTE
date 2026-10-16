# NuevaMente — Planning y definición funcional del Sprint 4

> **Documento de trabajo — versión 2 (12 de octubre de 2026).** Actualiza el planning de Sprint 4 con los acuerdos funcionales y las decisiones de arquitectura discutidas posteriormente, además de los hallazgos del código examinado en la rama `QA`. **No certifica implementación ni sustituye la validación de contratos y soluciones por los equipos.**

## 1. Propósito y contexto

Sprint 4 concentra el cierre e integración del producto educativo NuevaMente: generación de contenido adaptado mediante RAG, evaluación de calidad, revisión/corrección guiada por recomendaciones y preparación de pruebas y demostración final. El proyecto trabaja con las áreas **Agentes, BackendAPI, Data/IA, Frontend y QA**.

Se busca conservar el MVP ya construido y añadir el diferencial **multiagente con LangGraph**, sin reconstruir componentes que funcionan. La gestión del sprint debe priorizar el circuito completo y demostrable por encima de incorporar capacidades accesorias.

**Fuentes de referencia:** [repositorio del equipo](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE), rama `QA`; [tablero Trello](https://trello.com/b/sfLjGWmk/nuevamente-g10-latam-e7); revisión de código y acuerdos de esta conversación.

## 2. Resultado central del planning y de la revisión posterior

La propuesta que se ha trabajado establece **dos niveles de coordinación complementarios**:

- **BackendAPI orquesta el proceso de producto:** solicita generación o corrección a Agentes, llama directamente a Data/IA para evaluar, conserva resultados, estados e historial y controla el máximo de intentos.
- **LangGraph orquesta las capacidades inteligentes dentro del servicio Agentes:** Investigador RAG, Redactor Pedagógico y Agente Revisor.

**No existe una llamada directa de Agentes a Data/IA.** La evaluación siempre es solicitada por BackendAPI. Esta separación es esencial en los diagramas y en los contratos entre servicios.

La denominación acordada para Data/IA es **Agente Evaluador**; su trabajo consiste en evaluar el contenido y producir hallazgos, métricas y recomendaciones. El **Agente Revisor**, situado en Agentes/LangGraph, **no vuelve a evaluar**: procesa las recomendaciones que BackendAPI le entrega y coordina su aplicación.

### Estado de implementación verificado — 15 de octubre de 2026

Este documento conserva los objetivos y acuerdos funcionales del planning. El código revisado después de la versión de 12 de octubre muestra el siguiente estado:

- **LangGraph:** ya está incluido como dependencia y `agentes/graph.py` define grafos internos de generación. Sin embargo, la API activa de Agentes todavía usa el flujo directo de `AgentV1`; no hay endpoint HTTP `/api/v1/revise` implementado ni conectado a BackendAPI.
- **Evaluación semántica:** Data/IA expone `POST /evaluate/v2`, con señales heurísticas y semánticas separadas. BackendAPI está configurado para usar V2 y persiste las evaluaciones. El veredicto se deriva de la evaluación heurística; el proveedor semántico puede quedar `unavailable` si Gemini no está configurado.
- **Ciclo e historial:** BackendAPI devuelve en `GET /api/v1/documents/{id}/formats` `evaluation` y `evaluations` del ciclo asociado al formato seleccionado. También existe un endpoint de historial de generaciones/correcciones por formato, pero el Frontend no lo consulta: muestra las evaluaciones entregadas para el ciclo actual.
- **Corrección automática:** sigue desactivada por defecto (`AUTO_REVISION_ENABLED=false`) y no puede completarse de extremo a extremo mientras falte el endpoint de revisión en Agentes. La regeneración manual de formatos sí está implementada, pero no equivale a corregir basándose en recomendaciones.

## 3. Responsabilidades por componente

| Componente | Responsabilidad definida o propuesta |
| --- | --- |
| **BackendAPI** | Orquestación global; solicitudes a Agentes y Data/IA; persistencia de versiones, evidencias y evaluaciones; seguimiento de estados; límite de reintentos; tratamiento de fallos. |
| **Investigador RAG (Agentes)** | Recuperar los chunks pertinentes del documento previamente indexado; buscar evidencia adicional si el Revisor lo solicita. **No confundir recuperación con el pipeline de indexación.** |
| **Redactor Pedagógico (Agentes)** | Generar y corregir los formatos educativos mediante Gemini, atendiendo perfil, nicho, detalle y objetivos; mantener las salidas estructuradas. |
| **Agente Revisor (Agentes)** | Recibir contenido anterior, chunks y recomendaciones trasladadas por BackendAPI; determinar acciones de corrección, solicitar evidencia adicional al Investigador cuando haga falta y orientar al Redactor. **No emite una nueva evaluación de calidad.** |
| **Agente Evaluador (Data/IA)** | Analizar calidad pedagógica, relevancia, coherencia y soporte documental; exponer scores heurísticos y semánticos separados, hallazgos y recomendaciones. El veredicto V2 actual se deriva de la evaluación heurística. |
| **Frontend** | Solicitar acciones y presentar documentos, formatos, estados y resultados de evaluación; no orquestar el ciclo de revisión. |
| **QA** | Validar integración, recorridos de usuario, regresiones y escenario de demostración final. |

## 4. Flujos funcionales propuestos

### 4.1 Generación inicial propuesta

1. BackendAPI recibe la solicitud y el contexto de generación (documento, perfil, nicho, nivel, formato y, si corresponde, objetivo pedagógico).
2. BackendAPI llama al endpoint de generación de Agentes.
3. En el recorrido propuesto con LangGraph, **Investigador RAG → Redactor Pedagógico**: se recuperan chunks y se genera el contenido. En el endpoint activo, Agentes genera mediante el flujo directo de `AgentV1`, no con este grafo.
4. Agentes devuelve a BackendAPI contenido, evidencia utilizada y datos asociados.
5. **BackendAPI** solicita la evaluación al **Agente Evaluador de Data/IA**, incluyendo contenido, chunks y contexto.
6. Data/IA devuelve a BackendAPI veredicto, métricas, hallazgos y recomendaciones.
7. BackendAPI decide si la salida queda aceptada o requiere el ciclo de corrección, dentro de las reglas y límites que se acuerden.

### 4.2 Ciclo de corrección propuesto (aún no activo E2E)

1. Si Data/IA requiere cambios y hay intentos disponibles, BackendAPI llama al **nuevo endpoint del Agente Revisor**, enviando contenido anterior, chunks utilizados, contexto y recomendaciones; también debe disponer de información del intento.
2. En LangGraph, el **Revisor interpreta las recomendaciones** y prepara las acciones de corrección.
3. **Ruta condicional:** si necesita evidencia adicional, solicita recuperación al **Investigador RAG**; si no, conserva la evidencia ya disponible.
4. El **Redactor Pedagógico** produce la versión corregida. Si no se encuentra respaldo documental, no debe inventarlo: la revisión puede reformular u omitir la afirmación sin soporte.
5. Agentes devuelve a BackendAPI la versión corregida y los chunks utilizados (actualizados si corresponde).
6. **BackendAPI** vuelve a llamar a **Data/IA** para evaluar la nueva versión.
7. BackendAPI repite el ciclo hasta aprobación o hasta alcanzar el **máximo de reintentos de corrección**. **Configuración inicial acordada: un solo reintento automático**, lo que produce como máximo dos evaluaciones si ambas se completan (inicial y posterior a la corrección). El comportamiento del resultado final no aprobado y de los errores técnicos debe ser concretado por BackendAPI.

**Distinción funcional:** la **regeneración manual solicitada por el usuario** ya existe como operación de BackendAPI y actualmente relanza generación con el contexto original. **No es equivalente** a la corrección automática motivada por una evaluación.

### 4.3 Esquema textual del circuito

```mermaid
flowchart TB
    B1[BackendAPI solicita generación] --> A1[Agentes / LangGraph: Investigador RAG]
    A1 --> A2[Redactor Pedagógico]
    A2 --> B2[BackendAPI recibe contenido y chunks]
    B2 --> D[Data/IA: Agente Evaluador]
    D --> B3[BackendAPI recibe evaluación y recomendaciones]
    B3 --> Q{¿Requiere corrección y hay intentos?}
    Q -- No --> F[BackendAPI conserva resultado y estado final]
    Q -- Sí --> R[BackendAPI solicita revisión a Agentes]
    R --> AR[Agente Revisor]
    AR --> N{¿Necesita evidencia adicional?}
    N -- Sí --> I[Investigador RAG recupera más chunks]
    N -- No --> G[Redactor Pedagógico corrige]
    I --> G
    G --> B4[BackendAPI recibe versión corregida]
    B4 --> D
```

> Nota: el enlace BackendAPI → Data/IA es deliberadamente explícito. **LangGraph no invoca Data/IA** en esta propuesta.

## 5. Hallazgos del código existente — rama `QA`

### Agentes

- [`agentes/agent_v1.py`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/agentes/agent_v1.py): `AgentV1.answer()` **ya recupera evidencia** con `RetrieverService`, construye prompts adaptados y genera contenido con Gemini usando esquemas Pydantic. Retorna `content`, `sources_used`, estado y error. `extract_learning_metadata()` recupera información y obtiene metadatos pedagógicos.
- [`agentes/api.py`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/agentes/api.py): existe `/api/v1/index` para indexar documentos y `/api/v1/generate` para generación de los cuatro formatos. La generación itera formatos **secuencialmente**, pese al comentario de «paralela» que aparece en el archivo.
- [`agentes/requirements.txt`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/agentes/requirements.txt) incluye LangGraph y [`agentes/graph.py`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/agentes/graph.py) define grafos internos para generación y subgrafos por formato. El endpoint activo `/api/v1/generate` aún utiliza el flujo directo y secuencial de `AgentV1`; `api.py` no expone `/api/v1/revise`.
- La recuperación híbrida y los embeddings **ya existen**. La propuesta es **separar capacidades funcionales** dentro del grafo, reutilizándolas; **no duplicar el motor RAG ni rehacer la generación**.
- El flujo activo de `AgentV1.answer()` **no recibe contenido anterior ni recomendaciones correctivas**. El grafo/subgrafo interno no implica que exista un endpoint de revisión consumible por BackendAPI.

### BackendAPI

- [`adaptation_orchestration_service.py`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/backend/app/application/adaptation_orchestration_service.py): `complete_default_generation()` completa la generación, llama después a `_evaluate_completed_formats()` y persiste el paquete; los fallos de evaluación se tratan como **best-effort**, sin invalidar automáticamente la generación exitosa.
- [`format_generation_service.py`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/backend/app/application/format_generation_service.py): prepara intentos, solicita generación a Agentes y persiste los resultados.
- [`format_evaluation_service.py`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/backend/app/application/format_evaluation_service.py): envía a Data/IA `generated_content`, `chunks_used`, `generation_context`, documento y formato; guarda veredicto y observaciones.
- [`format_regeneration_service.py`](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO-7-NUEVAMENTE/blob/QA/backend/app/application/format_regeneration_service.py): prepara una **nueva generación manual** con parámetros previos, pero no utiliza automáticamente las recomendaciones de Data/IA para corregir.
- **Brecha de Sprint 4:** convertir la evaluación en una decisión de flujo (corregir, aceptar, agotar intentos) y llamar al **endpoint de revisión**, con persistencia y estados por intento.

### Data/IA

- Data/IA mantiene `POST /evaluate` (V1.1) y expone `POST /evaluate/v2` con evaluación heurística y semántica separadas. BackendAPI configura V2. El veredicto V2 se mapea desde la señal heurística; no hay una Decision Layer calibrada que combine los scores.
- El contrato V2 incluye `observations`, `recommendations` y `unsupported_information`; BackendAPI persiste y expone los resultados de evaluación. La ejecución de Gemini depende de configuración; sin ella, la señal semántica queda `unavailable` y la evaluación heurística puede continuar.
- La corrección automática basada en estas recomendaciones sigue pendiente de integración extremo a extremo porque Agentes no expone `/api/v1/revise` y Backend la mantiene desactivada por defecto.

## 6. Organización del trabajo según tarjetas de Sprint 4

Las tarjetas revisadas están agrupadas por área. **Que una tarjeta exista no demuestra que se haya completado**; verificar asignaciones, PR y estados actuales antes de reportar avance.

### Agentes

| Trabajo | Tarjeta |
| --- | --- |
| Ajustes de PR pendiente | [197](https://trello.com/c/wBPvXJPq/197) |
| Modelar e implementar causas de fallo Gemini | [198](https://trello.com/c/TDQoSSDi/198) |
| **Implementar arquitectura multiagente (LangGraph)** | [200](https://trello.com/c/te4MqGt8/200) |
| **Implementar el rol de Agente Revisor** | [201](https://trello.com/c/7Gzx5TsK/201) |
| Contrato del Revisor con Data/IA | [202](https://trello.com/c/kSHPs5s4/202) |
| **Endpoint para BackendAPI del Agente Revisor** | [203](https://trello.com/c/kTqfwyqy/203) |
| Pruebas de integración | [204](https://trello.com/c/F1Yi4tPm/204) |
| Retornar título y descripción corta del documento | [220](https://trello.com/c/JkkPXheg/220) |

**Interpretación de alcance acordada:** la tarea **LangGraph** monta el grafo y separa/reutiliza Investigador y Redactor; la tarea **Revisor** añade la lógica para aplicar recomendaciones; la tarea **Endpoint** expone la operación al Backend. Son entregables diferentes, aunque conectados.

### BackendAPI

| Trabajo | Tarjeta |
| --- | --- |
| Captura de errores de Gemini | [199](https://trello.com/c/DXh2B7QW/199) |
| Implementar llamada al Revisor | [205](https://trello.com/c/sianoWdN/205) |
| Acordar contratos de entrada y salida de revisión con Agentes | [206](https://trello.com/c/W5rAleoO/206) |
| Implementar número de reintentos | [207](https://trello.com/c/itdTsuBO/207) |
| Controlar y retornar estados del proceso de revisión | [208](https://trello.com/c/DHS1WZZP/208) |
| Unificar revisión anterior y actual y actualizar | [209](https://trello.com/c/5gTQpzvY/209) |
| Pruebas de integración | [210](https://trello.com/c/C4RFflQN/210) |
| Gestión de errores del Revisor | [211](https://trello.com/c/L2nMB8Bb/211) |
| Documentación | [212](https://trello.com/c/WD0mhznE/212) |
| **Inactivar** documentos, sin eliminación física | [218](https://trello.com/c/VM5c6slz/218) |
| Capturar título y descripción del archivo | [222](https://trello.com/c/oh5iJukj/222) |

### Data/IA

| Trabajo | Tarjeta |
| --- | --- |
| Actualizar contrato Data/IA–Backend | [193](https://trello.com/c/UbvCpqUD/193) |
| Contrato con Frontend para métricas | [196](https://trello.com/c/XvZ4UebJ/196) |
| Diseñar e implementar evaluador semántico | [190](https://trello.com/c/UGCqpVGX/190) |
| Integrar evaluador semántico con heurístico | [191](https://trello.com/c/VaA2hfTF/191) |
| Crear dataset de calibración heurístico vs. semántico | [192](https://trello.com/c/YCZ2OM1K/192) |
| Pruebas de integración | [194](https://trello.com/c/wTcsSMoZ/194) |
| Documentación | [195](https://trello.com/c/Hl5iiWrI/195) |

### Frontend y QA

- **Frontend:** refinamientos de interfaz (texto, tipografía, colores, logo, diseño adaptable), comportamiento de actualización de estados de carga, visualización de métricas del evaluador por formato y pestañas; acción de **inactivación lógica** de documentos (no borrar físicamente).
- **QA:** pruebas funcionales, integración extremo a extremo, revisión entre pares y preparación/validación de los casos de demo/pitch.
- En esta consolidación **no se incluyen IDs individuales de estas tarjetas que no se recuperaron expresamente en la revisión previa**.

## 7. Contratos y dependencias críticas

**Cadena de dependencia principal:**

`Data/IA: hallazgos accionables y veredicto` → `BackendAPI: persistir, decidir, reenviar` → `Agentes: revisión/corrección` → `BackendAPI: reevaluar`.

Brechas que siguen abiertas para una integración definitiva:

1. **Ejecución de la corrección automática:** la API de revisión de Agentes y su integración con BackendAPI siguen pendientes; definir y validar el contrato de revisión cuando se habilite ese recorrido.
2. **Estados y cierre del ciclo automático:** al integrar revisión, distinguir fallos de Gemini, fallos de evaluación, ausencia de evidencia, contenido aprobado, corrección requerida y agotamiento de intentos. La configuración actual mantiene deshabilitada la revisión automática.
3. **Historial completo en la interfaz:** Frontend muestra las evaluaciones (`evaluations`) que Backend entrega para el ciclo actual, pero no consume la ruta `/history` para recorrer todos los ciclos históricos por formato.
4. **Validación E2E:** validar corrección y reevaluación entre BackendAPI, Agentes, Data/IA y Frontend cuando exista un endpoint de revisión consumible.

Los contratos de evaluación V2 y el agrupamiento de evaluaciones del ciclo actual ya están implementados. Estos puntos describen brechas del recorrido de corrección automática y del acceso visual al historial completo; no implican que toda la evaluación o persistencia esté pendiente.

## 8. Nuevo acuerdo funcional: ciclo, evaluaciones y respuesta al Frontend

### 8.1 Qué se entiende por «ciclo»

Un **ciclo de generación y corrección** comienza cuando se solicita generar un formato para un documento y su contexto pedagógico. Abarca **la generación inicial, la evaluación inicial y, si Data/IA solicita mejoras y aún hay reintentos disponibles, las correcciones automáticas y sus evaluaciones posteriores**. Termina cuando Data/IA aprueba el contenido o BackendAPI alcanza el límite de correcciones configurado.

**Regla inicial del sprint: máximo un reintento automático de corrección.** Por ello, si la primera evaluación no aprueba y la corrección/reevaluación se completan, habrá **dos evaluaciones**. Si la primera aprueba, habrá **una**. Después de implementar el recorrido mínimo, el equipo medirá duración y decidirá si conviene permitir más reintentos. Un error técnico no debe presumirse equivalente a evaluación aprobada o reprobada; sus estados requieren diseño específico.

Este concepto de ciclo es **un requisito de agrupación funcional**, no la obligación de añadir una columna `cycle_id`, un contador en cada evaluación o una tabla nueva. BackendAPI deberá analizar la relación adecuada entre generaciones y evaluaciones y presentar una solución al equipo.

### 8.2 Secuencia de interacción BackendAPI ↔ Data/IA

1. BackendAPI obtiene el contenido de la generación inicial y los chunks de respaldo.
2. BackendAPI solicita **una evaluación** a Data/IA enviando contenido, tipo de formato, documento, evidencia y contexto pedagógico.
3. Data/IA aplica Evaluation V2 y devuelve `verdict`, `heuristic_scores` y `semantic_evaluation`, con observaciones, recomendaciones y afirmaciones no respaldadas. El veredicto actual se deriva de la señal heurística; los scores semánticos permanecen separados. **Data/IA no guarda ni ensambla el historial de métricas para Frontend.**
4. **BackendAPI guarda la evaluación al recibirla**, sea favorable o no. Actualmente esta persistencia ya existe.
5. Si el contenido requiere mejoras y resta un reintento, BackendAPI pide la corrección al servicio Agentes; luego envía la versión corregida a Data/IA, que genera **otra evaluación independiente**.
6. BackendAPI vuelve a guardar esa evaluación; decide si termina por aprobación o por límite de reintentos.
7. Cuando termina el ciclo, **BackendAPI construye la respuesta para Frontend**: último contenido generado de cada formato y lista de evaluaciones de **ese último ciclo**, ordenada de la **más reciente a la más antigua**.

**Distinción esencial:** el Agente Evaluador **identifica los problemas y propone mejoras**; el Agente Revisor de LangGraph recibe esas recomendaciones por BackendAPI y coordina su aplicación. **No hay llamada directa Agentes → Data/IA.**

### 8.3 Lo que Frontend debe recibir y presentar

**Comportamiento funcional acordado (sin prescribir modal, pestañas, pantalla o componente):**

- **Un único contenido por tipo de formato**: la versión vigente al finalizar el último ciclo. **No** se solicita mostrar un historial de versiones del contenido.
- **Historial de métricas de evaluación solo del último ciclo de ese formato**: primera posición para la evaluación final o más reciente y después las anteriores en orden descendente.
- El usuario debe poder apreciar que hubo revisión y si mejoraron las métricas. Si no hubo corrección, se muestra la única evaluación disponible; si el ciclo no pudo completarse, los estados deben reflejarlo sin aparentar aprobación.
- El historial es **por formato** (quiz, flashcards, tldr, video_script), no una mezcla indiscriminada de evaluaciones del documento.

**Ejemplo conceptual de la respuesta final BackendAPI → Frontend** — no es un contrato establecido ni el JSON actual del sistema:

```json
{
  "document_id": "doc_123",
  "formats": {
    "quiz": {
      "format_id": "fmt_002",
      "status": "success",
      "content": { "title": "Quiz corregido", "instructions": "...", "questions": [] },
      "evaluations": [
        {
          "evaluation_id": "eval_002",
          "status": "aprobado",
          "scores": {
            "relevance": 5,
            "coherence": 5,
            "didactic_adaptation": 4,
            "content_support": 5
          }
        },
        {
          "evaluation_id": "eval_001",
          "status": "requiere_revision",
          "scores": {
            "relevance": 4,
            "coherence": 3,
            "didactic_adaptation": 2,
            "content_support": 4
          }
        }
      ]
    }
  }
}
```

> El ejemplo ilustra **forma y orden**, no datos reales ni campos definitivos; `questions: []` es una abreviación gráfica, no un ejemplo de contenido válido para los esquemas de generación. El equipo definirá la forma real de la respuesta.

### 8.4 Estado que confirma el código de BackendAPI, Data/IA y Frontend

| Capacidad | Situación verificada al 15 de octubre de 2026 |
| --- | --- |
| Generaciones múltiples de un documento | **Existe**: `FormatGenerationService.prepare_generation()` crea nuevos `format_id`; la regeneración manual crea registros adicionales, sin sobrescribir generaciones anteriores. |
| Historial de generaciones | **Existe internamente**: `SQLiteGeneratedFormatRepositoryAdapter.find_by_document_id()` consulta todas las generaciones del documento. |
| Formato vigente y evaluaciones del ciclo actual para Frontend | **Existe**: `GET /documents/{document_id}/formats` devuelve el contenido seleccionado con `evaluation` y `evaluations` del ciclo pertinente. El Frontend muestra esas evaluaciones en el modal y permite recorrerlas. |
| Historial completo de evaluaciones/correcciones | **Existe en Backend**: `GET /documents/{document_id}/formats/{format_type}/history` agrupa ciclos por formato. **El Frontend no consume este endpoint**; su vista actual muestra las evaluaciones entregadas para el ciclo del formato. |
| Guardado y presentación de evaluaciones | **Existe**: Backend persiste cada evaluación con `evaluation_id` y `format_id`; Data/IA V2 devuelve scores heurísticos y semánticos separados, hallazgos y recomendaciones. |
| Evaluación V2 integrada | **Existe**: Data/IA expone `/evaluate/v2` y BackendAPI lo tiene configurado. El veredicto se deriva del evaluador heurístico; no existe una Decision Layer calibrada que combine ambos scores. |
| Corrección automática basada en recomendaciones y reintentos | **Pendiente E2E**: Backend tiene la capacidad condicional, desactivada por defecto; falta el endpoint `/api/v1/revise` en Agentes. La regeneración manual existente no es una corrección automática guiada por evaluación. |

**Campos de la integración de evaluación:** Backend envía a Data/IA `document_id`, `format`, `generated_content`, `chunks_used` y `generation_context`; asocia después la evaluación con el `format_id` persistido. V2 expone scores heurísticos y semánticos en cuatro dimensiones (`relevance`, `coherence`, `didactic_adaptation`, `content_support`), además de `observations`, `recommendations`, `unsupported_information`, versiones de evaluator/rúbrica y metadatos semánticos.

**Ajuste de términos frente a diagramas exploratorios:** los JSON de las imágenes son conceptuales y no deben tratarse como contrato literal. En V2, la entrada utiliza `document_id`, `format`, `generated_content`, `generation_context` y `chunks_used`; la respuesta incluye `verdict`, `heuristic_scores` y `semantic_evaluation`. El endpoint V1.1 `/evaluate` conserva los nombres de su contrato anterior (`status`, `scores`, `informacion_no_respaldada`, `observaciones`).

### 8.5 Qué se solicita al equipo, sin imponer implementación

- **Data/IA:** el contrato V2 ya expone hallazgos y recomendaciones, y Backend lo consume; validar que la calidad de esas recomendaciones resulte suficiente para un flujo automático de revisión.
- **BackendAPI:** ya persiste evaluaciones y devuelve el contenido seleccionado con métricas de su ciclo actual. Sigue pendiente activar y probar la decisión y el reintento automático junto al endpoint de Agentes.
- **Frontend:** ya muestra el resultado de evaluación y permite navegar entre las evaluaciones del ciclo actual. No consulta el endpoint de historial completo por formato; incorporarlo a la interfaz sería un alcance adicional.

El requisito funcional de presentar el contenido seleccionado con evaluaciones del ciclo actual está implementado en la respuesta de `/formats` y en la vista del Frontend. El ejemplo conceptual anterior continúa describiendo el objetivo de orden de las evaluaciones, no un JSON contractual.

### 8.6 Esquema de las responsabilidades del ciclo

```mermaid
flowchart TB
    subgraph CICLO[Un ciclo: generación inicial + evaluación + correcciones permitidas]
        B[BackendAPI recibe contenido generado] --> D[BackendAPI solicita evaluación a Data/IA]
        D --> E[Data/IA devuelve métricas, veredicto y recomendaciones]
        E --> P[BackendAPI guarda esta evaluación]
        P --> Q{¿Aprobado o sin reintentos disponibles?}
        Q -- No --> C[BackendAPI solicita corrección a Agentes]
        C --> N[BackendAPI recibe nuevo contenido]
        N --> D
    end
    Q -- Sí --> J[BackendAPI reúne contenido vigente e historial de evaluaciones de este ciclo]
    J --> F[Frontend: último contenido + evaluaciones, más reciente primero]
```

---

## 9. Qué se consideró viable y qué no se propone

**Decisiones de diseño discutidas y aceptadas como base de la propuesta:**

- Separar Investigador RAG y Redactor Pedagógico como **roles** en LangGraph, reutilizando `AgentV1` y el RAG existente.
- Añadir un Agente Revisor que **aplica las recomendaciones** del Evaluador y puede solicitar nueva recuperación al Investigador.
- Mantener Data/IA como **Agente Evaluador externo** a LangGraph y a BackendAPI como orquestador del ciclo global.
- Mantener separadas **generación inicial**, **corrección automática** y **regeneración manual del usuario**.
- Implementar un circuito **acotado** y demostrable en el sprint final.

**No se recomendó** rehacer ChromaDB, chunking, embeddings o algoritmos de recuperación; migrar el Backend completo a LangGraph; introducir autonomía abierta, múltiples memorias persistentes o complejidad adicional que no contribuya a la entrega.

## 10. Riesgos, viabilidad y verificación pendiente

| Riesgo / tema | Revisión necesaria |
| --- | --- |
| Contratos desalineados entre equipos | Validar un mismo payload y campos semánticos de evaluación/corrección en Data/IA, Backend y Agentes. |
| Correcciones poco útiles | Verificar que las observaciones de Data/IA permiten efectuar cambios concretos; no limitarse a notas genéricas. |
| Duplicación de responsabilidad | Evitar que el Revisor vuelva a puntuar el contenido o que Agentes decida reintentos globales. |
| Regresión del MVP | Conservar indexación, los cuatro formatos estructurados, metadatos y `sources_used`. |
| Revisión sin respaldo | Si la nueva búsqueda no aporta chunks suficientes, la versión corregida debe evitar inventar evidencia. |
| Estados incongruentes | Definir cómo cerrar intentos fallidos y qué mostrar si vence el límite sin aprobación. |
| Alcance temporal | Priorizar integración básica y pruebas E2E frente a características no esenciales. |
| Revisión final de código | Contrastarla con PR/commits y avances posteriores a la rama `QA` observada; este README refleja la revisión disponible, no una auditoría de despliegue. |

## 11. Resultado esperado para la validación de Sprint 4

Un recorrido reproducible que permita demostrar que:

1. Se utiliza un documento previamente indexado y un contexto pedagógico.
2. El **Investigador RAG** recupera evidencia y el **Redactor Pedagógico** genera contenido educativo estructurado.
3. BackendAPI recibe contenido y evidencia y **llama a Data/IA**.
4. Data/IA genera evaluación con métricas y recomendaciones.
5. Si corresponde corrección, BackendAPI llama al **endpoint del Revisor**.
6. El Revisor aplica la recomendación a través del Redactor, solicitando nuevos chunks solo si hace falta.
7. BackendAPI vuelve a evaluar y termina al obtener aprobación o alcanzar el límite de intentos.
8. BackendAPI entrega al Frontend **solo el contenido vigente** de cada formato y **todas las métricas del último ciclo**, de la evaluación más reciente a la inicial; no expone contenido de versiones anteriores en esta vista.

**Este es un criterio propuesto de demostración e integración, no evidencia de que el recorrido completo esté operativo.**

### 10.1 Evaluación de viabilidad del sprint

La evaluación de viabilidad que sigue corresponde al planning del 12 de octubre, no al estado actual. A la fecha de la revisión (15 de octubre), LangGraph y la evaluación semántica V2 ya están en el código; BackendAPI persiste las evaluaciones y entrega al Frontend las métricas del ciclo actual. La **corrección automática E2E** sigue pendiente porque Agentes no expone `/api/v1/revise` y BackendAPI la mantiene deshabilitada. También queda por validar el recorrido E2E desplegado; la existencia de estos componentes no certifica por sí sola la integración productiva ni el cumplimiento de las tarjetas del sprint.

## 12. Diagramas de referencia

- [Arquitectura y responsabilidades](<ArquitecturaResponsabilidades.png>) — separación de responsabilidades entre servicios.
- [Flujo de funcionamiento de NuevaMente](<Flujo de funcionamiento de NuevaMente.png>) — generación y ciclo de evaluación/corrección propuestos.
- [Ciclo de evaluación y corrección de IA](<Ciclo de evaluación y corrección de IA.png>) — evaluación, persistencia y devolución de métricas.
- [Arquitectura general Sprint 4](<NuevaMente_ Arquitectura General Sprint 4.png>) — comunicación entre servicios.

Las imágenes están en el repositorio y representan la arquitectura/flujo propuestos; no certifican que el recorrido completo de corrección automática esté implementado.

---

**Estado de este documento:** planning funcional actualizado con una nota de implementación verificada al 15 de octubre de 2026. La evaluación V2, persistencia y presentación de evaluaciones del ciclo actual están implementadas; la corrección automática sigue siendo una propuesta no activa de extremo a extremo. El endpoint de historial completo existe en Backend, pero aún no se consume desde Frontend. La planificación y la existencia de código no sustituyen la validación de los acuerdos por la Project Manager ni una prueba E2E desplegada.
