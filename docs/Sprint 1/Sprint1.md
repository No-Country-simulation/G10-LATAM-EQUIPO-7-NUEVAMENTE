# Sprint 1 — Review, decisiones y aprendizajes

**Proyecto:** NuevaMente
**Sprint:** 1
**Fecha de cierre:** 25 de septiembre de 2026

---

## 1. Propósito del Sprint

Sprint 1 tuvo como objetivo construir la **base técnica y funcional necesaria para comenzar a integrar NuevaMente como producto**, sin pretender completar todavía el sistema final ni la arquitectura multiagente.

El trabajo se distribuyó entre Frontend, Backend API, Agentes/RAG, Data/IA, Infraestructura y QA/Integración.

| Área             | Alcance principal del Sprint 1                                                            |
| ---------------- | ----------------------------------------------------------------------------------------- |
| Frontend         | Modularización, carga de documentos y evolución inicial de UI/UX                          |
| Backend API      | Carga y procesamiento de documentos, identificación, persistencia y almacenamiento en OCI |
| Agentes          | Agent V1, extracción, limpieza, chunking, embeddings, Vector Store y retrieval            |
| Data / IA        | Corpus de evaluación, Ground Truth, contrato de retrieval y métricas                      |
| Infraestructura  | OCI Object Storage, VM y preparación de infraestructura                                   |
| QA / Integración | Flujo Git, Pull Requests, validación, integración y documentación                         |

El resultado principal del Sprint no es todavía un producto completo, sino un conjunto de componentes funcionales que empiezan a establecer contratos e integraciones entre sí.

---

# 2. Referencia de producto

Durante el Sprint se reforzó un criterio importante para la toma de decisiones:

> **El documento oficial de requerimientos del proyecto funciona como nuestra principal referencia de producto.**

Las propuestas visuales, técnicas o funcionales pueden ampliar y mejorar la experiencia planteada originalmente, pero cualquier decisión que modifique comportamiento, alcance o arquitectura debe contrastarse primero con esa referencia.

Esto permite diferenciar entre:

**evolucionar conscientemente el producto** y
**modificarlo accidentalmente como consecuencia de una decisión aislada de diseño o implementación.**

---

# 3. Frontend

## Resultado general

Frontend presentó una evolución visual importante y una creativa propuesta de experiencia basada en una biblioteca de documentos. 
El usuario puede cargar documentación que posteriormente queda representada dentro de la interfaz como contenido disponible para consulta y estudio.

La Demo Review permitió detectar que algunas decisiones de experiencia de usuario empiezan a tener implicaciones funcionales y arquitectónicas que deben definirse explícitamente.

## Formatos de salida

El requerimiento base del proyecto puede representarse conceptualmente como:

`documento + formato solicitado → resultado`

La interfaz actual abre la posibilidad de que un mismo documento disponga de varios formatos de estudio. Esto plantea una decisión de producto pendiente:

**¿NuevaMente genera un único formato solicitado por el usuario o genera múltiples formatos asociados al documento?**

A partir de esa decisión será necesario definir además cuándo ocurre la generación:

`al procesar el documento`

`al abrir el documento`

o

`cuando el usuario solicita específicamente un formato`.

Esta decisión afecta directamente a Backend, Agentes, persistencia, tiempos de procesamiento y consumo de modelos. 
Una opción arquitectónica que permite mantener flexibilidad consiste en conservar una operación base:

`documento + formato → resultado`

y permitir que posteriormente una capa de orquestación solicite múltiples formatos cuando la experiencia visual lo requiera.

## Persistencia

También deberá definirse si los contenidos generados se almacenan o se producen nuevamente bajo demanda. En caso de persistencia, Frontend debe continuar consumiendo esa información mediante Backend API y no acceder directamente a almacenamiento o base de datos.

## Caso de uso empresarial

La experiencia visual actual está especialmente orientada al aprendizaje y educación técnica. Sin embargo, NuevaMente también contempla casos de uso para equipos de desarrollo y áreas de tecnología.

Por ejemplo, una organización podría cargar documentación interna de arquitectura y generar versiones adaptadas para diferentes públicos:

`Junior → Semi Senior → Arquitectura / perfil experto → Ejecutivo`

Durante la Demo Review surgió como posible dirección conceptual explorar experiencias diferenciadas similares a:

**Educativa / Empresarial**

Antes de incorporar este tipo de cambio al código se recomienda explorarlo mediante wireframes o mockups y determinar qué elementos cambian realmente entre ambos contextos.

## Otros puntos identificados

Dentro de la evolución de Frontend también se identificaron como áreas a considerar la búsqueda dentro de la biblioteca, la revisión de colorimetría, la representación adecuada de errores del Backend, la navegabilidad y la consolidación del flujo completo del usuario antes de ampliar nuevas pantallas.

---

# 4. Backend API

## Resultado general

Backend API presentó un cierre técnico sólido para el alcance del Sprint. El flujo construido permite avanzar sobre:

`archivo → validación → document_id → identificación/deduplicación → metadata → almacenamiento OCI`

y existe además capacidad de recuperación del documento almacenado. No se identificaron durante la Demo Review replanteamientos importantes sobre la arquitectura construida.

## Integración Frontend → Backend → OCI

Como cierre operativo del Sprint se definió comprobar el recorrido completo:

`Frontend → Backend API → OCI`

La prueba debe validar que un documento cargado desde la interfaz sea recibido correctamente por Backend, procesado y almacenado finalmente en Object Storage.

## Manejo de errores
Además del flujo exitoso, la experiencia debe contemplar los errores producidos durante el procesamiento.

El objetivo esperado es:

`Backend detecta error → devuelve respuesta estructurada → Frontend comunica el problema al usuario`

El manejo de errores se considera parte de la calidad funcional del producto y debe verificarse dentro de las integraciones.

---

# 5. Agentes / RAG

## Alcance de Sprint 1

El objetivo principal de Agentes durante este Sprint fue construir el núcleo del sistema RAG.

Los componentes desarrollados incluyen:

`extracción → limpieza → chunking → embeddings → Vector Store → retrieval`

También se construyó la estructura inicial de Agent V1 y el contrato necesario para interoperar con Data/IA. La generación pedagógica final, la adaptación completa del contenido y la arquitectura multiagente corresponden a etapas posteriores del proyecto.

## Estado técnico

Al cierre del Sprint se encuentran implementados los principales componentes del pipeline RAG:

| Componente               | Estado        |
| ------------------------ | ------------- |
| Agent V1                 | Implementado  |
| Extracción PDF/MD/TXT    | Implementada  |
| Limpieza y normalización | Implementada  |
| Chunking                 | Implementado  |
| Embeddings multilingües  | Implementados |
| Vector Store             | Implementado  |
| Retrieval                | Implementado  |
| Contrato para evaluación | Implementado  |

El sistema dispone además de una salida estructurada para evaluación que incluye elementos como `case_id`, `document_id`, ranking, score, `top_k` y estados de respuesta.

## Frontera Backend ↔ Agentes

El principal pendiente funcional consiste en cerrar la entrada productiva del documento desde Backend hacia Agentes. Conceptualmente:

`Backend recupera documento + document_id → Agentes recibe → pipeline RAG procesa`

Esto requiere cerrar el contrato entre ambos componentes y adaptar las funciones del pipeline para trabajar con documentos provenientes del flujo real de la aplicación.

## Demo reproducible del RAG

Para facilitar la demostración técnica del Sprint se solicitó construir una ejecución reproducible del pipeline. Esta demostración puede ejecutarse por consola y debe reutilizar las funciones reales del RAG.

## Coordinación interna

Durante el Sprint se presentó trabajo paralelo sobre algunas mismas funcionalidades. Esto evidenció la necesidad de reforzar la coordinación interna dentro de las áreas cuando varias personas participan en un mismo componente.
Para próximos Sprints será conveniente que los equipos definan responsables y alcance de cada tarea, evitando implementar simultáneamente soluciones equivalentes en ramas diferentes.

---

# 6. Data / IA

## Resultado general

Data/IA presentó uno de los procesos más consistentes del Sprint. El trabajo permitió construir una base controlada para medir objetivamente el comportamiento del RAG.

Se avanzó en:

`corpus de evaluación → Ground Truth → chunks controlados → contrato de retrieval → resultados → métricas`

Se establecieron además mecanismos para trabajar con métricas como Recall@K y Precision@K. Esta capa resulta especialmente importante porque permite que las decisiones sobre retrieval no dependan únicamente de percepción subjetiva.
El trabajo realizado proporciona una base medible para continuar ajustando embeddings, chunking y recuperación durante las siguientes iteraciones.

---

# 7. Infraestructura

## OCI Object Storage

Durante Sprint 1 se configuró la infraestructura necesaria para almacenar los documentos originales. El diseño mantiene una separación clara de responsabilidades:

`Frontend → Backend → OCI`

Backend es responsable de interactuar con Object Storage.
Agentes recibe posteriormente el documento mediante el contrato establecido con Backend y no necesita conectarse directamente a OCI.

## Máquina virtual

También se logró disponer de una máquina virtual para continuar evolucionando el entorno de integración.
Aunque finalmente la VM no quedó dentro de Free Tier, la infraestructura ya permite comenzar durante el siguiente Sprint el despliegue de Backend y Frontend.
Esto permitirá sustituir gradualmente direcciones y entornos locales por servicios más estables y compartidos.

---

# 8. QA, Pull Requests e integración

Durante Sprint 1 se consolidó el siguiente flujo de integración:

`desarrollo en rama`

`↓`

`validación interna`

`↓`

`actualización respecto a la rama destino`

`↓`

`Pull Request`

`↓`

`QA / integración`

`↓`

`rama estable`

Se reforzó además la importancia de mantener los Pull Requests acotados al área responsable.

## Calidad técnica

Durante las revisiones aparecieron observaciones relacionadas con documentación, estructura, archivos innecesarios, ramas desactualizadas, código reemplazado y otros detalles que individualmente pueden parecer menores.
El criterio adoptado fue considerar estos elementos como parte de la calidad del entregable y no como trabajo opcional posterior.
Una funcionalidad no debería considerarse completamente terminada únicamente porque ejecuta correctamente su caso de uso principal. También debe procurar dejar el repositorio en un estado mantenible.

## Código obsoleto

A medida que el proyecto evoluciona, algunas implementaciones iniciales dejan de formar parte del flujo vigente.
Mantener simultáneamente código antiguo y código nuevo aumenta el riesgo de:
* reutilizar accidentalmente implementaciones obsoletas;
* duplicar lógica;
* dificultar mantenimiento;
* confundir futuras contribuciones;
* inducir a herramientas de IA a utilizar rutas que ya no pertenecen a la arquitectura vigente.

Por ello, una vez verificadas las dependencias, el código reemplazado debería eliminarse o identificarse explícitamente como obsoleto.

---

# 9. Responsabilidad de calidad y QA

La separación entre revisión técnica de código y QA funcional no estuvo completamente definida.
En la práctica, QA comenzó a asumir parte de la revisión de Pull Requests y Project Management realiza revisiones técnicas sobre integración, contratos, estructura, deuda técnica y coherencia entre componentes.

Esto permitió detectar varios problemas antes de integrar código, pero también evidenció una debilidad del proceso actual: no existe todavía una capa estable de revisión técnica previa a QA.

Esto no se plantea como el modelo definido dentro del proyecto, sino como una consecuencia de la disponibilidad real del equipo durante Sprint 1.
Con la cantidad actual de personas participando de manera sostenida será necesario encontrar un equilibrio entre autonomía de los desarrolladores, peer review e integración, procurando que QA pueda concentrarse progresivamente en validación funcional sin perder las barreras de calidad que durante este Sprint resultaron necesarias.

---

# 10. Desarrollo asistido por IA

Las herramientas de IA están formando parte activa del proceso de desarrollo del proyecto.
A medida que el repositorio y sus integraciones crecen, también aumenta el riesgo de que una herramienta:

* sobrescriba código válido;
* duplique implementaciones;
* pierda contexto;
* modifique componentes fuera del alcance de una tarea;
* ignore contratos existentes;
* utilice código obsoleto.

Por ello, para las siguientes iteraciones se recomienda trabajar sobre **unidades funcionales pequeñas y verificables**.

El ciclo sugerido es:

`cambio funcional concreto`

`→ generación/modificación asistida por IA`

`→ revisión del diff`

`→ pruebas`

`→ validación de integración`

`→ siguiente cambio`

Git funciona así no solo como repositorio, sino también como mecanismo de control sobre las modificaciones realizadas con asistencia de IA.

---

# 11. Pendientes de cierre de Sprint 1

Al finalizar la Demo Review permanecieron algunos puntos necesarios para completar el cierre técnico del Sprint.

| Pendiente                                                 | Área               |
| --------------------------------------------------------- | ------------------ |
| Validar flujo real Frontend → Backend → OCI               | Frontend / Backend |
| Preparar demo reproducible del RAG                        | Agentes            |
| Cerrar contrato de entrada Backend → Agentes              | Backend / Agentes  |
| Adaptar pipeline RAG a documentos recibidos desde Backend | Agentes            |
| Completar integración pendiente hacia QA                  | Agentes / QA       |
| Completar validaciones finales correspondientes al Sprint | Data / IA          |
| Actualizar documentación y README                         | Transversal        |
| Preparar evidencia/video final del Sprint                 | Transversal        |

---

# 12. Retrospectiva

## Lo que funcionó

Sprint 1 permitió construir componentes técnicos reales en prácticamente todas las áreas necesarias para comenzar a integrar NuevaMente.

Backend consiguió establecer el flujo de documentos y almacenamiento.

Agentes implementó el núcleo RAG.

Data/IA proporcionó mecanismos objetivos para evaluar retrieval.

Frontend evolucionó suficientemente para permitir discutir decisiones reales de experiencia y producto.

Infraestructura permitió disponer de OCI y una máquina virtual.

También comenzaron a definirse contratos concretos entre componentes que hasta ahora se habían desarrollado principalmente de forma independiente.

## Aspectos a mejorar

El Sprint mostró que algunas integraciones ocurrieron demasiado cerca del cierre, reduciendo el margen disponible para QA, correcciones y preparación de demos.

También apareció trabajo paralelo sobre funcionalidades equivalentes, lo que evidencia la necesidad de mejorar coordinación y asignación dentro de algunas áreas.

La revisión de Pull Requests mostró además oportunidades para mejorar la calidad de las entregas antes de llegar a QA.

Finalmente, el crecimiento del producto está aumentando la importancia de analizar el impacto transversal de cada decisión: una modificación en Frontend puede afectar Backend; un cambio en Agentes puede afectar Data/IA; y un contrato mal definido puede bloquear varias áreas simultáneamente.

---

# 13. Sugerencias generales para Sprint 2

### Trabajar por funcionalidades pequeñas y verificables

Especialmente al trabajar con herramientas de IA, realizar cambios acotados, revisar los diffs y validar cada modificación antes de ampliar el alcance.

### Integrar de forma incremental

No esperar al final del Sprint para conectar componentes.

Los avances que ya estén probados y funcionales deberían comenzar a integrarse durante el desarrollo.

### Comunicar dependencias y responsabilidades

Cuando varias personas o áreas intervengan sobre una misma funcionalidad, definir previamente responsables, contratos y alcance.

### Considerar la calidad técnica parte de “terminado”

Pruebas, documentación, manejo de errores, limpieza del código, ramas actualizadas y reducción de deuda técnica forman parte de la entrega.

### Pensar siempre en un único producto

Aunque NuevaMente esté dividido en áreas técnicas, el objetivo final no es producir varios componentes independientes.

Cada cambio debe considerar cómo se integra con el resto del sistema.

---

# Conclusión

Sprint 1 establece una base técnica real sobre la cual continuar construyendo
Frontend, Backend, RAG, evaluación e infraestructura.Existen implementaciones concretas y comienzan a aparecer contratos e integraciones entre ellas.


> **Sprint 1 construyó las piezas. Sprint 2 debe empezar a convertirlas en un solo producto funcional.**
