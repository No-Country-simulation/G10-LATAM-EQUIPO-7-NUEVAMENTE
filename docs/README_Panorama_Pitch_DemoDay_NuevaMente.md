# NuevaMente — Panorama base para Pitch / Demo Day

**Objetivo de este documento**  
Conservar, sin resumir en exceso, las respuestas base a los puntos solicitados para el Demo Day. Este documento no es todavía el guion del pitch ni la presentación final. Es el panorama de partida sobre el cual se construirá después la narrativa, la demo y la distribución del tiempo.

---

## 1. Problema identificado

La documentación técnica contiene conocimiento valioso, pero muchas veces **no está escrita para enseñar** y puede resultar inaccesible para personas con distintos niveles de conocimiento.

Un mismo manual necesita explicarse de manera diferente según el perfil o rol del destinatario. No aprende de la misma manera una persona principiante, un desarrollador, un arquitecto o una persona ejecutiva.

Por eso, para convertirse en material realmente educativo, la información técnica debe ser **reescrita, ejemplificada y estructurada** con un nivel de profundidad y un tono adecuados para quien la va a aprender.

El problema, por tanto, no es únicamente “tener documentación”, sino **convertir conocimiento técnico en contenido realmente enseñable para públicos diferentes, manteniendo la fidelidad respecto de la fuente original**.

---

## 2. Solución desarrollada

NuevaMente es una plataforma inteligente que transforma documentación técnica en contenido educativo adaptado al perfil del destinatario.

### 2.1 Transformación pedagógica personalizada

La plataforma recibe documentación técnica y adapta el contenido considerando variables como:

- perfil del destinatario;
- nicho o contexto de aplicación;
- nivel de profundidad;
- objetivo de aprendizaje, cuando corresponde.

La solución no se limita a cambiar el formato del contenido: busca ajustar la forma de explicar el conocimiento al contexto pedagógico del usuario.

### 2.2 Cuatro formatos educativos complementarios

A partir de un mismo documento se generan cuatro formatos:

- **Resumen ejecutivo / TLDR:** sintetiza los principales contenidos del documento.
- **Flashcards:** presentan conceptos relevantes de forma breve para repaso y memorización.
- **Quiz:** permite comprobar comprensión mediante preguntas, opciones y explicaciones.
- **Guion formativo para video:** propone una estructura narrativa para explicar el contenido e incluye narración y sugerencias visuales o de escenas.

Estos formatos son complementarios: permiten trabajar el mismo conocimiento desde diferentes formas de aprendizaje.

### 2.3 Recuperación de información específica según el formato

NuevaMente no utiliza necesariamente los mismos fragmentos del documento para construir todos los formatos.

Cada formato realiza su propia recuperación de información relevante. Por ejemplo, un resumen ejecutivo puede requerir evidencia diferente a la utilizada para construir flashcards, conceptos clave o preguntas de un quiz.

Por tanto, **el formato no solo cambia la presentación final: también influye en qué evidencia del documento es recuperada para construir el contenido**.

### 2.4 Información pedagógica adicional del documento

Además de los cuatro formatos, la solución entrega información general útil para orientar el aprendizaje, como:

- descripción del documento;
- conceptos clave;
- conocimientos o prerrequisitos previos;
- tiempo estimado de estudio o lectura, según la definición final del producto.

### 2.5 Biblioteca y experiencia de consulta

La solución dispone de una biblioteca de documentos con dos formas de visualización:

- una vista interactiva tipo estantería;
- una vista tipo lista, más directa y potencialmente útil en contextos empresariales.

La biblioteca permite consultar documentos cargados previamente, buscarlos, filtrarlos y acceder a su detalle.

### 2.6 Consulta y descarga del documento original

Desde la propia plataforma se puede acceder a la información general del documento y también **descargar nuevamente el archivo original**.

### 2.7 Regeneración de contenidos

La plataforma permite regenerar uno o varios formatos sin tener que volver a cargar o reindexar el documento desde cero.

Esto permite producir una nueva versión de un contenido manteniendo el contexto pedagógico asociado al documento.

### 2.8 Evaluación y trazabilidad

Las generaciones conservan la evidencia recuperada desde el documento que sirvió para producir cada contenido.

Posteriormente, la solución puede evaluar el resultado considerando aspectos como:

- relevancia;
- coherencia;
- adaptación didáctica;
- respaldo documental.

Esto permite que la generación de contenido y la evaluación de su calidad sean responsabilidades separadas.

---

## 3. Cómo funciona el proyecto

NuevaMente está dividido en cuatro componentes principales, cada uno con responsabilidades diferenciadas.

### 3.1 Frontend

Es la capa de interacción con el usuario.

Se encarga de:

- presentar la biblioteca de documentos;
- permitir la carga de nuevos archivos;
- permitir seleccionar parámetros pedagógicos;
- mostrar información general del documento;
- presentar los cuatro formatos educativos;
- mostrar estados, resultados y evaluaciones;
- permitir regeneraciones;
- permitir la descarga del documento original.

El Frontend no ejecuta directamente los procesos de IA ni accede directamente a la infraestructura interna. Se comunica con el producto a través de BackendAPI.

### 3.2 BackendAPI

BackendAPI funciona como **orquestador global del producto**.

Se encarga de:

- recibir las solicitudes del Frontend;
- administrar el ciclo de vida de los documentos;
- gestionar metadata técnica y pedagógica;
- comunicarse con OCI Object Storage para almacenar y recuperar archivos;
- persistir documentos, formatos, metadata, evidencias y evaluaciones;
- coordinar las llamadas al componente de Agentes;
- coordinar las llamadas al componente Data/IA;
- gestionar estados del proceso;
- decidir cuándo un contenido debe aceptarse, evaluarse o entrar en revisión;
- controlar el número permitido de reintentos del ciclo de corrección.

### 3.3 Sistema de Agentes

El componente de Agentes concentra las capacidades inteligentes de recuperación, generación y revisión.

La arquitectura de trabajo contempla tres roles principales:

#### Investigador RAG

- recupera del documento los chunks o fragmentos más pertinentes;
- aporta evidencia para la generación;
- puede realizar una nueva búsqueda si el Revisor determina que hace falta información adicional.

#### Redactor Pedagógico

- genera los formatos educativos;
- utiliza la evidencia recuperada;
- adapta el contenido al perfil, nicho, nivel y objetivo pedagógico;
- produce salidas estructuradas;
- genera nuevas versiones durante un proceso de corrección.

#### Agente Revisor

- recibe las observaciones o recomendaciones provenientes del proceso de evaluación;
- interpreta qué debe corregirse;
- decide si la evidencia existente es suficiente;
- puede solicitar nueva evidencia al Investigador RAG;
- orienta al Redactor Pedagógico para producir una versión corregida.

El Revisor no reemplaza al Evaluador: sus responsabilidades son diferentes.

### 3.4 Data/IA — Agente Evaluador

Data/IA funciona como componente independiente de evaluación.

Recibe desde Backend:

- el contenido generado;
- el contexto pedagógico;
- los chunks utilizados como evidencia.

Evalúa aspectos como:

- relevancia;
- coherencia;
- adaptación didáctica;
- respaldo documental.

Devuelve a Backend métricas, estado de evaluación, observaciones y recomendaciones para que Backend determine cómo continuar el flujo.

### 3.5 Flujo general

El funcionamiento general puede entenderse así:

**Frontend solicita → Backend orquesta → Agentes recupera evidencia y genera → Backend envía el resultado a Data/IA → Data/IA evalúa → Backend decide.**

Si el contenido requiere ajustes y existen intentos disponibles:

**Backend → Agente Revisor → posible nueva recuperación RAG → Redactor Pedagógico → Backend → nueva evaluación Data/IA.**

El ciclo termina cuando el contenido es aceptado o cuando se alcanza el límite de correcciones configurado.

### 3.6 Infraestructura y despliegue

Los servicios se ejecutan en contenedores Docker independientes coordinados mediante Docker Compose sobre una máquina virtual de Oracle Cloud Infrastructure (OCI).

La arquitectura de despliegue contempla:

- Nginx como punto de entrada público;
- contenedores separados por servicio;
- persistencia fuera del ciclo de vida de los contenedores;
- OCI Object Storage para archivos originales y artefactos generados;
- integración y despliegue automatizados mediante GitHub Actions;
- construcción de imágenes y despliegue hacia la infraestructura de OCI.

---

## 4. Principales funcionalidades

### 4.1 Biblioteca de documentos

Permite:

- consultar documentos cargados previamente;
- buscarlos;
- filtrarlos;
- seleccionarlos;
- alternar entre vista de lista y estantería interactiva;
- acceder al detalle de cada documento.

### 4.2 Carga y transformación de documentos

Permite cargar documentación técnica y definir su contexto pedagógico para transformarla en contenido educativo adaptado.

La solución procesa el documento y genera los formatos pedagógicos correspondientes.

### 4.3 Consulta general del documento

Permite acceder a información como:

- descripción;
- conceptos clave;
- conocimientos o prerrequisitos;
- tiempo estimado de estudio o lectura;
- documento original.

Además, permite descargar el archivo fuente.

### 4.4 Centro de capacitación

Permite consultar los cuatro formatos principales:

- resumen ejecutivo;
- flashcards;
- quiz;
- guion formativo para video.

El guion incluye narración y sugerencias visuales o de escenas para apoyar la creación de un video educativo.

### 4.5 Regeneración de formatos

Permite solicitar una nueva generación de uno o varios formatos sin volver a cargar ni reindexar el documento.

---

## 5. Cómo trabajó el equipo

El proyecto se organizó por áreas funcionales:

- Frontend;
- Backend;
- Agentes;
- Data/IA;
- Infraestructura;
- QA / Integración.

### 5.1 Trabajo por sprints

Se trabajó utilizando una dinámica ágil basada en sprints.

En cada sprint:

- se definía un objetivo común;
- se establecían los entregables esperados;
- se identificaban dependencias y bloqueos;
- las tareas generales se organizaban en Trello;
- cada equipo mantenía autonomía para dividir esas tareas en subtareas y distribuir responsabilidades internamente.

Esto permitía conservar un objetivo común sin centralizar todas las decisiones técnicas.

### 5.2 Ceremonias y seguimiento

Se realizaron ceremonias como:

- Planning;
- Daily meetings;
- Review / Demo meeting.

Las dailies permitían revisar avances, detectar bloqueos y levantar necesidades de coordinación durante la semana.

Las reviews permitían revisar el resultado del sprint, identificar ajustes y procurar que el siguiente sprint comenzara con la menor cantidad posible de pendientes del anterior.

### 5.3 Contratos antes de la integración

Una práctica importante fue procurar definir primero los contratos de integración entre componentes.

Antes de que todos los servicios estuvieran terminados, los equipos podían acordar:

- schemas;
- payloads;
- estructuras de entrada y salida;
- estados;
- contratos mock.

Esto permitía que Backend, Frontend, Agentes y Data/IA trabajaran en paralelo sobre interfaces conocidas.

### 5.4 Pull Requests e integración progresiva

Los cambios se entregaban progresivamente mediante Pull Requests.

El flujo general consistía en:

- trabajo del equipo sobre su rama;
- validación interna;
- actualización frente a la rama base;
- apertura de PR hacia la rama de integración / QA;
- revisión técnica;
- integración;
- pruebas funcionales y de integración;
- paso de lo validado hacia la rama estable.

### 5.5 Revisión técnica y peer review

Antes de considerar una integración como terminada se realizaba una etapa de revisión técnica y peer review orientada a:

- revisar coherencia general del código;
- validar contratos;
- detectar fallos de integración;
- revisar responsabilidades entre componentes;
- evitar introducir deuda técnica innecesaria.

### 5.6 Integración Continua

Se incorporó una capa de **CI — Continuous Integration / Integración Continua** mediante GitHub Actions.

Esta capa permite ejecutar validaciones y tests automáticamente al momento de integrar cambios o generar Pull Requests, funcionando como una primera barrera de calidad antes de la integración manual y funcional.

### 5.7 Despliegue Continuo

El flujo contempla también una capa de **CD — Continuous Delivery / Continuous Deployment**, mediante la cual una versión integrada y validada puede avanzar automáticamente hacia el proceso de construcción y despliegue en la infraestructura.

### 5.8 Comunicación continua

Discord funcionó como canal permanente de coordinación durante la semana.

Los equipos lo utilizaron para:

- acuerdos internos;
- contratos entre componentes;
- resolución de bloqueos;
- coordinación de dependencias;
- levantamiento de necesidades;
- seguimiento técnico fuera de las ceremonias formales.

---

## 6. Resultados o avances alcanzados

### 6.1 Flujo funcional de extremo a extremo

Se logró integrar un recorrido funcional que permite:

- cargar un documento;
- almacenarlo;
- indexarlo;
- generar contenido educativo;
- persistir resultados;
- consultar posteriormente los formatos desde la aplicación.

### 6.2 Experiencia de usuario completa

Se construyó una interfaz gráfica funcional, agradable y flexible, que incluye:

- biblioteca;
- búsqueda y filtros;
- carga de documentos;
- selección de contexto pedagógico;
- consulta general del documento;
- centro de capacitación;
- cuatro formatos educativos;
- regeneración;
- descarga del original.

### 6.3 Arquitectura modular y desacoplada

Se consolidó una arquitectura con responsabilidades separadas entre:

- Frontend;
- Backend;
- Agentes / RAG;
- Data/IA;
- persistencia;
- almacenamiento;
- infraestructura.

El objetivo fue evitar concentrar toda la lógica en un único servicio y permitir que cada componente pudiera evolucionar manteniendo contratos claros.

### 6.4 Calidad y trazabilidad

La solución incorpora mecanismos para:

- conservar la evidencia utilizada en cada generación;
- evaluar posteriormente el contenido generado;
- separar generación y evaluación;
- conservar historial de generaciones y evaluaciones;
- validar estructuras de entrada y salida.

### 6.5 Confiabilidad técnica

Se desarrollaron mecanismos de:

- manejo explícito de errores;
- estados de procesamiento;
- validación de contratos;
- deduplicación de documentos;
- persistencia histórica;
- recuperación y descarga de archivos;
- manejo de fallos entre servicios.

Además, existen pruebas unitarias y de integración sobre diferentes partes del flujo.

### 6.6 Infraestructura reproducible

Se construyó una base de despliegue basada en:

- Docker;
- Docker Compose;
- OCI;
- Nginx;
- GitHub Actions;
- automatización de CI/CD.

### 6.7 Diferencial multiagente

La arquitectura final plantea un sistema multiagente con responsabilidades estructuradas y separadas:

- Investigador RAG;
- Redactor Pedagógico;
- Agente Revisor;
- Agente Evaluador externo en Data/IA.

Este diferencial debe considerarse como resultado final del proyecto **si el recorrido completo queda integrado y validado de extremo a extremo antes del Demo Day**.

---

## 7. Impacto o valor que genera la solución

### 7.1 Hace más accesible el conocimiento técnico

NuevaMente permite partir de documentación técnica compleja y convertirla en material adaptado a personas con diferentes perfiles y niveles de conocimiento.

El mismo conocimiento puede ser presentado con distinta profundidad, estructura y tono según quién necesita aprenderlo.

El valor pedagógico central es que la documentación deja de ser únicamente un recurso de consulta y puede convertirse en una experiencia de aprendizaje personalizada.

### 7.2 Facilita una preparación más estructurada

NuevaMente no entrega únicamente una respuesta generada.

La solución proporciona distintas herramientas para trabajar el mismo conocimiento:

- resumen para comprender y sintetizar;
- flashcards para repasar y memorizar;
- quiz para comprobar comprensión;
- guion para explicar o convertir el contenido en material audiovisual;
- conceptos clave;
- prerrequisitos;
- tiempo estimado de estudio.

Esto permite al usuario **comprender, repasar, memorizar y evaluar su propio aprendizaje** utilizando diferentes formatos complementarios.

### 7.3 Reduce el esfuerzo para convertir documentación en capacitación

La creación manual de materiales educativos a partir de documentación técnica puede requerir tiempo de especialistas, diseñadores instruccionales y perfiles técnicos.

NuevaMente automatiza una parte importante de ese proceso al:

- procesar la documentación;
- recuperar información relevante;
- generar diferentes formatos;
- adaptar el contenido al destinatario;
- evaluar posteriormente la calidad del resultado.

El valor está en **reducir el tiempo y el esfuerzo necesarios para transformar documentación técnica en material de capacitación utilizable**.

### 7.4 Genera una base reutilizable, confiable e integrable

El valor de NuevaMente no termina en su interfaz actual.

Por un lado, la solución busca mantener los contenidos vinculados con la documentación original mediante recuperación de evidencia y evaluación del respaldo documental, reduciendo el riesgo de presentar como aprendizaje información que no esté sustentada en la fuente.

Por otro lado, la arquitectura está desacoplada: Backend expone contratos estructurados y mantiene separadas la presentación, la lógica de producto, la generación y la evaluación.

Esto permite que, a futuro, las mismas capacidades puedan integrarse con:

- otros frontends;
- plataformas educativas;
- sistemas corporativos;
- aplicaciones internas;
- otros canales de consumo.

Por tanto, NuevaMente no se plantea únicamente como una interfaz web cerrada, sino como una base tecnológica capaz de adaptarse a diferentes contextos educativos o empresariales.

---

## Nota de trabajo para el pitch

Este documento conserva el panorama completo. **No debe reducirse todavía a frases de pitch.**

La siguiente etapa será decidir:

- qué partes son esenciales para el jurado;
- cuáles se muestran durante la demo;
- cuáles se cuentan verbalmente mientras el sistema procesa;
- cuáles quedan visibles únicamente en arquitectura o slides;
- cuáles deben eliminarse por tiempo.

El pitch final debe construirse a partir de este panorama, no reemplazarlo.
