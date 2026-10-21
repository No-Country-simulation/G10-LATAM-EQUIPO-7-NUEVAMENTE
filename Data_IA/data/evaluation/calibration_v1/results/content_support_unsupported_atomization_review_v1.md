# Content Support — Unsupported Atomization Review v1

## Objetivo

Analizar los claims humanos `unsupported` para determinar si el fallo de soporte pertenece al claim completo o a una subafirmación específica.

`chunks_used` es la única evidencia factual válida.

No se modifica el ground truth en esta etapa.

## Categorías de atomicidad

- `atomic_unsupported`: una sola afirmación factual y esa afirmación no está respaldada.
- `mixed_compound`: combina contenido respaldado y una subafirmación no respaldada.
- `relation_unsupported`: los hechos base están respaldados, pero una relación temporal, causal, comparativa, condicional o lógica no lo está.
- `unclear_segmentation`: no puede dividirse de forma fiable sin alterar el significado.

---

## 1. CAL-V1-004 — `scene_1_narration_claim_2`

**Formato:** `video_script`

**Legacy ratio:** `0.7272727272727273`
**Legacy needs review:** `True`

### Claim original

También afirma que los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.

### Ground truth humano

`unsupported`

**Human notes:**

Los chunks no respaldan despliegue autónomo de modelos ni ausencia de supervisión humana.

### Resultado semántico

**semantic_supported:** `unsupported`

**semantic_reason:**

Los chunks proporcionados no mencionan nada acerca de que los agentes de IA puedan desplegar modelos en producción de forma autónoma sin supervisión humana.

### Evidencia — chunks_used

#### `AI-ES-002_CH_001`

```text
# Introducción a la inteligencia artificial y los agentes generativos

- Módulo

- 7 Unidades

La inteligencia artificial genera aplicaciones que pueden crear contenido, responder preguntas y ayudar con tareas. En este módulo, explorará los aspectos básicos de la inteligencia artificial generativa, incluidos los modelos de lenguaje grande (LLM), las solicitudes y los agentes de IA.

## Objetivos de aprendizaje

Al término de este módulo, sabrá hacer lo siguiente:

- Describir los conceptos básicos de la inteligencia artificial generativa.
- Explicar cómo funcionan los modelos de lenguaje (LLM) de gran tamaño.
- Considere cómo crear solicitudes eficaces para los LLM.
- Describir los conceptos básicos de los agentes y las soluciones de inteligencia artificial agente.
```

#### `AI-ES-002_CH_002`

```text
- Describir los conceptos básicos de los agentes y las soluciones de inteligencia artificial agente.

## Requisitos previos

Antes de iniciar este módulo, debería tener lo siguiente:
- Familiaridad con los conceptos y la terminología de la inteligencia artificial
- Principios básicos de aprendizaje automático.

- Introducción min
- Modelos de lenguaje grandes (LLM) min
- Mensajes min
- Agentes de IA min
- Ejercicio: Exploración de la inteligencia artificial generativa min
- Evaluación del módulo min
- Resumen min
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---

## 2. CAL-V1-006 — `key_point_3_claim_1`

**Formato:** `tldr`

**Legacy ratio:** `0.8`
**Legacy needs review:** `True`

### Claim original

El decorador cifra automáticamente todas las respuestas GET.

### Ground truth humano

`unsupported`

**Human notes:**

Los chunks no mencionan cifrado automático de respuestas GET.

### Resultado semántico

**semantic_supported:** `unsupported`

**semantic_reason:**

La evidencia no menciona en ningún momento que el decorador cifre automáticamente las respuestas GET, sino que indica que sirve para asociar una función a una operación y path determinados.

### Evidencia — chunks_used

#### `BE-ES-001_CH_013`

```text
Normalmente usas:

- POST : para crear datos.
- GET : para leer datos.
- PUT : para actualizar datos.
- DELETE : para eliminar datos.

Así que, en OpenAPI, cada uno de los métodos HTTP se llama una operación.

#### Define un path operation decorator

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

El @app.get("/") le dice a FastAPI que la función justo debajo se encarga de manejar requests que vayan al path / usando una operación get.
```

#### `BE-ES-001_CH_014`

```text
La sintaxis @algo en Python se llama un decorador. Lo pones encima de una función. Un decorador toma la función de abajo y hace algo con ella. En este caso, este decorador le dice a FastAPI que la función de abajo corresponde al path / con una operación get. Es el path operation decorator. También puedes usar @app.post(), @app.put(), @app.delete(), @app.options(), @app.head(), @app.patch() y @app.trace().
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---

## 3. CAL-V1-014 — `question_1_explanation_claim_2`

**Formato:** `quiz`

**Legacy ratio:** `0.625`
**Legacy needs review:** `True`

### Claim original

Además, usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.

### Ground truth humano

`unsupported`

**Human notes:**

El chunk no contiene información sobre mejora automática del posicionamiento SEO.

### Resultado semántico

**semantic_supported:** `unsupported`

**semantic_reason:**

Los chunks_used explican qué es HTML y para qué sirven sus etiquetas, pero no mencionan en ningún momento que el uso de etiquetas HTML mejore automáticamente el posicionamiento SEO.

### Evidencia — chunks_used

#### `FE-ES-001_CH_002`

```text
## ¿Qué es HTML?

HTML (HyperText Markup Language, por sus siglas en inglés) es un lenguaje de marcado que indica a los navegadores web cómo estructurar las páginas web que visita. Puede ser tan complicado o tan simple como el desarrollador web quiera que sea. HTML consiste en una serie de elementos, que utiliza para encerrar, envolver o marcar diferentes partes del contenido para que aparezca o actúe de cierta manera. Las etiquetas pueden convertir el contenido en un hipervínculo para conectarse a otra página, poner palabras en cursiva, etc.
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---

## 4. CAL-V1-015 — `card_2_back_claim_2`

**Formato:** `flashcards`

**Legacy ratio:** `0.6666666666666666`
**Legacy needs review:** `True`

### Claim original

Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

### Ground truth humano

`unsupported`

**Human notes:**

Los chunks respaldan que existen cuatro bloques fundamentales, pero no respaldan la afirmación adicional de que estén 'sin una secuencia clara'.

### Resultado semántico

**semantic_supported:** `unsupported`

**semantic_reason:**

Los chunks mencionan los cuatro bloques fundamentales (bucles, funciones, condicionales y eventos), pero no afirman que estén "sin una secuencia clara".

### Evidencia — chunks_used

#### `FE-ES-002_CH_001`

```text
# Elementos básicos de JavaScript

En este módulo, continuamos nuestra cobertura de todas las características clave de JavaScript, tornando nuestra atención a tipos de código comúnmente encontrados tales como enunciados condicionales, bucles (loops), funciones, y eventos. Ya has visto estas cosas en este curso, pero solo de pasada aquí lo hablaremos mas explícitamente.
```

#### `FE-ES-002_CH_007`

```text
La siguiente evaluación probara tu entendimiento de lo básico de Javascript cubierto en las guias anteriores.

Ahora que hemos visto los bloques constructores fundamentales de JavaScript, probaremos tus conocimientos en bucles, funciones, condicionales y eventos construyendo un item bastante común en muchos sitios web — una galería de imágenes creada con JavaScript.
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---

## 5. CAL-V1-016 — `conclusion_claim_1`

**Formato:** `tldr`

**Legacy ratio:** `0.9090909090909091`
**Legacy needs review:** `True`

### Claim original

El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### Ground truth humano

`unsupported`

**Human notes:**

El chunk no establece explícitamente un desacoplamiento entre ocurrencia notificable y lógica reactiva; es una extrapolación respecto de la evidencia disponible.

### Resultado semántico

**semantic_supported:** `unsupported`

**semantic_reason:**

Los chunks utilizados no mencionan el paradigma dirigido por eventos ni el desacoplamiento entre ocurrencias notificables y lógica reactiva.

### Evidencia — chunks_used

#### `FE-ES-002_CH_006`

```text
Los eventos son acciones u ocurrencias que aparecen durante la ejecución del programa, y que son reportadas por el sistema, de forma que se pueda responder a los eventos de la forma deseada. Por ejemplo, si un usuario hace un click en un botón de una página web, puede que se quiera que ese evento inicie una acción en el que se muestre cierta información en un cuadro de información. En este último artículo se presentarán y describirán los conceptos necesarios con respecto a los eventos, y como funcionan en un navegador.
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---

## 6. CAL-V1-018 — `card_1_back_claim_2`

**Formato:** `flashcards`

**Legacy ratio:** `1.0`
**Legacy needs review:** `True`

### Claim original

También cifra automáticamente todo el tráfico del clúster por defecto.

### Ground truth humano

`unsupported`

**Human notes:**

Los chunks no afirman que Kubernetes cifre automáticamente todo el tráfico del clúster.

### Resultado semántico

**semantic_supported:** `unsupported`

**semantic_reason:**

Los chunks no mencionan el cifrado automático de tráfico en el clúster.

### Evidencia — chunks_used

#### `CLD-ES-001_CH_002`

```text
Kubernetes tiene varias características. Puedes pensar en Kubernetes como:

- una plataforma de contenedores
- una plataforma de microservicios
- una plataforma portable de nube

y mucho más.

Kubernetes ofrece un entorno de administración centrado en contenedores. Kubernetes orquesta la infraestructura de cómputo, redes y almacenamiento para que las cargas de trabajo de los usuarios no tengan que hacerlo. Esto ofrece la simplicidad de las Plataformas como Servicio (PaaS) con la flexibilidad de la Infraestructura como Servicio (IaaS) y permite la portabilidad entre proveedores de infraestructura.
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---

## 7. CAL-V1-020 — `scene_2_narration_claim_1`

**Formato:** `video_script`

**Legacy ratio:** `0.0`
**Legacy needs review:** `False`

### Claim original

Antes de eso, la serie enseña conceptos básicos de la nube.

### Ground truth humano

`unsupported`

**Human notes:**

El chunk respalda que la serie enseña conceptos básicos de la nube, pero no establece la relación temporal 'Antes de eso'.

### Resultado semántico

**semantic_supported:** `supported`

**semantic_reason:**

El texto de la evidencia indica explícitamente que la serie de cuatro partes enseña conceptos básicos de la nube.

### Evidencia — chunks_used

#### `CLD-ES-002_CH_002`

```text
¿Primera experiencia con la nube? Introducción a la infraestructura en la nube es una serie de cuatro partes que le enseña conceptos básicos de la nube, proporciona una visión general simplificada de muchos servicios de Azure y le guía con ejercicios prácticos para implementar sus primeros servicios de forma gratuita. Complete todas las rutas de aprendizaje de la serie si está preparando el examen AZ-900: Aspectos básicos de Microsoft Azure.

Esta es la primera ruta de aprendizaje de la serie Introducción a la infraestructura en la nube: Descripción de los conceptos de la nube. Las otras rutas son parte 2: Descripción de la arquitectura y los servicios de Azure, parte 3: Descripción de la administración y gobernanza de Azure y parte 4: Aplicación de aptitudes de Azure en proyectos guiados.
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---

## 8. CAL-V1-020 — `scene_2_narration_claim_2`

**Formato:** `video_script`

**Legacy ratio:** `0.5`
**Legacy needs review:** `True`

### Claim original

Después volvemos a los ejercicios y otra vez a los servicios de Azure.

### Ground truth humano

`unsupported`

**Human notes:**

Los chunks mencionan ejercicios prácticos y servicios de Azure, pero no establecen que se vuelva a ellos posteriormente ni esa secuencia temporal concreta.

### Resultado semántico

**semantic_supported:** `unsupported`

**semantic_reason:**

Los chunks no mencionan ni implican que se vuelva a los ejercicios y a los servicios de Azure tras haber hecho otra cosa.

### Evidencia — chunks_used

#### `CLD-ES-002_CH_002`

```text
¿Primera experiencia con la nube? Introducción a la infraestructura en la nube es una serie de cuatro partes que le enseña conceptos básicos de la nube, proporciona una visión general simplificada de muchos servicios de Azure y le guía con ejercicios prácticos para implementar sus primeros servicios de forma gratuita. Complete todas las rutas de aprendizaje de la serie si está preparando el examen AZ-900: Aspectos básicos de Microsoft Azure.

Esta es la primera ruta de aprendizaje de la serie Introducción a la infraestructura en la nube: Descripción de los conceptos de la nube. Las otras rutas son parte 2: Descripción de la arquitectura y los servicios de Azure, parte 3: Descripción de la administración y gobernanza de Azure y parte 4: Aplicación de aptitudes de Azure en proyectos guiados.
```

### Revisión de atomicidad

**atomization_type:** `PENDING`

**atomic_claim_1:** PENDING

**atomic_claim_1_support:** `PENDING`

**atomic_claim_2:** PENDING

**atomic_claim_2_support:** `PENDING`

**atomic_claim_3:** PENDING

**atomic_claim_3_support:** `PENDING`

**analysis_notes:** PENDING

---
