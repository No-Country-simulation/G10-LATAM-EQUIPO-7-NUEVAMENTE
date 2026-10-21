# Claim Atomization v1 — Manual Review Packet

## Objetivo

Definir manualmente el ground truth de atomización antes de probar cualquier atomizador automático.

`chunks_used` es la única evidencia válida para asignar `expected_support` a cada átomo.

La atomización debe preservar todo el significado factual del claim original.

## Reglas

- No inventar información que no exista en el source claim.
- No eliminar calificadores relevantes como `automáticamente`, `todos`, `antes`, `después`, `sin`, `por defecto`, etc.
- No dividir por longitud; dividir por proposiciones o relaciones factuales independientes.
- Un claim ya atómico debe conservarse como un solo átomo.
- Cada átomo debe poder evaluarse de forma independiente.
- `expected_support` puede ser `supported`, `unsupported` o `uncertain`.

Tipos permitidos:

- `factual_proposition`
- `temporal_relation`
- `causal_relation`
- `conditional_relation`
- `comparative_relation`
- `negation_or_absence`
- `scope_or_quantifier`

---

## 1. ATOM-V1-001 — CAL-V1-004

**source_claim_id:** `scene_1_narration_claim_2`

**format:** `video_script`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

También afirma que los agentes de IA pueden desplegar modelos en producción de forma autónoma sin supervisión humana.

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

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 2. ATOM-V1-002 — CAL-V1-006

**source_claim_id:** `key_point_3_claim_1`

**format:** `tldr`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

El decorador cifra automáticamente todas las respuestas GET.

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

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 3. ATOM-V1-003 — CAL-V1-014

**source_claim_id:** `question_1_explanation_claim_2`

**format:** `quiz`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

Además, usar etiquetas HTML mejora automáticamente el posicionamiento SEO de una página.

### Evidencia — chunks_used

#### `FE-ES-001_CH_002`

```text
## ¿Qué es HTML?

HTML (HyperText Markup Language, por sus siglas en inglés) es un lenguaje de marcado que indica a los navegadores web cómo estructurar las páginas web que visita. Puede ser tan complicado o tan simple como el desarrollador web quiera que sea. HTML consiste en una serie de elementos, que utiliza para encerrar, envolver o marcar diferentes partes del contenido para que aparezca o actúe de cierta manera. Las etiquetas pueden convertir el contenido en un hipervínculo para conectarse a otra página, poner palabras en cursiva, etc.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 4. ATOM-V1-004 — CAL-V1-015

**source_claim_id:** `card_2_back_claim_2`

**format:** `flashcards`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

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

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 5. ATOM-V1-005 — CAL-V1-016

**source_claim_id:** `conclusion_claim_1`

**format:** `tldr`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

El paradigma dirigido por eventos desacopla la ocurrencia notificable de la lógica reactiva que procesa dicha señal.

### Evidencia — chunks_used

#### `FE-ES-002_CH_006`

```text
Los eventos son acciones u ocurrencias que aparecen durante la ejecución del programa, y que son reportadas por el sistema, de forma que se pueda responder a los eventos de la forma deseada. Por ejemplo, si un usuario hace un click en un botón de una página web, puede que se quiera que ese evento inicie una acción en el que se muestre cierta información en un cuadro de información. En este último artículo se presentarán y describirán los conceptos necesarios con respecto a los eventos, y como funcionan en un navegador.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 6. ATOM-V1-006 — CAL-V1-018

**source_claim_id:** `card_1_back_claim_2`

**format:** `flashcards`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

También cifra automáticamente todo el tráfico del clúster por defecto.

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

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 7. ATOM-V1-007 — CAL-V1-020

**source_claim_id:** `scene_2_narration_claim_1`

**format:** `video_script`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

Antes de eso, la serie enseña conceptos básicos de la nube.

### Evidencia — chunks_used

#### `CLD-ES-002_CH_002`

```text
¿Primera experiencia con la nube? Introducción a la infraestructura en la nube es una serie de cuatro partes que le enseña conceptos básicos de la nube, proporciona una visión general simplificada de muchos servicios de Azure y le guía con ejercicios prácticos para implementar sus primeros servicios de forma gratuita. Complete todas las rutas de aprendizaje de la serie si está preparando el examen AZ-900: Aspectos básicos de Microsoft Azure.

Esta es la primera ruta de aprendizaje de la serie Introducción a la infraestructura en la nube: Descripción de los conceptos de la nube. Las otras rutas son parte 2: Descripción de la arquitectura y los servicios de Azure, parte 3: Descripción de la administración y gobernanza de Azure y parte 4: Aplicación de aptitudes de Azure en proyectos guiados.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 8. ATOM-V1-008 — CAL-V1-020

**source_claim_id:** `scene_2_narration_claim_2`

**format:** `video_script`

**human_support_label:** `unsupported`

**selection_reason:** `unsupported_case`

### Source claim

Después volvemos a los ejercicios y otra vez a los servicios de Azure.

### Evidencia — chunks_used

#### `CLD-ES-002_CH_002`

```text
¿Primera experiencia con la nube? Introducción a la infraestructura en la nube es una serie de cuatro partes que le enseña conceptos básicos de la nube, proporciona una visión general simplificada de muchos servicios de Azure y le guía con ejercicios prácticos para implementar sus primeros servicios de forma gratuita. Complete todas las rutas de aprendizaje de la serie si está preparando el examen AZ-900: Aspectos básicos de Microsoft Azure.

Esta es la primera ruta de aprendizaje de la serie Introducción a la infraestructura en la nube: Descripción de los conceptos de la nube. Las otras rutas son parte 2: Descripción de la arquitectura y los servicios de Azure, parte 3: Descripción de la administración y gobernanza de Azure y parte 4: Aplicación de aptitudes de Azure en proyectos guiados.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 9. ATOM-V1-009 — CAL-V1-001

**source_claim_id:** `question_1_explanation_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

El módulo introduce los tipos de soluciones que la inteligencia artificial puede hacer posible y considera prácticas de inteligencia artificial responsable.

### Evidencia — chunks_used

#### `AI-ES-001_CH_001`

```text
# Introducción a los conceptos de inteligencia artificial

- Módulo

- 10 Unidades

¿Tiene curiosidad por la inteligencia artificial? ¿Quieres entender de qué trata el revuelo? En este módulo se presenta el mundo de la inteligencia artificial.

## Objetivos de aprendizaje

En este módulo, obtendrá información sobre los tipos de soluciones que la inteligencia artificial puede hacer posible y tener en cuenta las prácticas de inteligencia artificial responsables.

## Requisitos previos

Aunque no es necesario, un conocimiento conceptual del aprendizaje automático puede ser útil para este módulo. Considere la posibilidad de completar la introducción a los conceptos de Machine Learning antes de iniciar este módulo.

- Introducción a la IA min
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 10. ATOM-V1-010 — CAL-V1-003

**source_claim_id:** `key_point_1_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

Crear solicitudes eficaces para LLM.

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

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 11. ATOM-V1-011 — CAL-V1-005

**source_claim_id:** `card_1_back_claim_1`

**format:** `flashcards`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

La clase FastAPI, importada desde el paquete fastapi mediante: from fastapi import FastAPI.

### Evidencia — chunks_used

#### `BE-ES-001_CH_001`

```text
# Primeros Pasos

El archivo FastAPI más simple podría verse así:

```text
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

Copia eso en un archivo main.py.

FastAPI tiene una extensión oficial para VS Code (y Cursor), que proporciona varias funcionalidades.

Ejecuta el servidor en vivo con `uv run fastapi dev`.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 12. ATOM-V1-012 — CAL-V1-009

**source_claim_id:** `summary_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

El módulo enseña a almacenar y manipular datos en Python, incluyendo el uso de variables, operaciones numéricas y conversión de tipos.

### Evidencia — chunks_used

#### `DS-ES-001_CH_001`

```text
# Trabajar con datos en Python

- Módulo

- 7 Unidades

Aprenda a almacenar y manipular datos en Python. Explore variables, escritura dinámica, operaciones numéricas y conversión de tipos.

## Objetivos de aprendizaje

Después de completar este módulo, puede hacer lo siguiente:

- Almacene y actualice los valores mediante variables.
- Realice operaciones aritméticas con números.
- Convertir entre tipos de datos mediante funciones integradas.

- Ejercicio: Cálculo del GPA de un alumno.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 13. ATOM-V1-013 — CAL-V1-013

**source_claim_id:** `scene_1_narration_claim_1`

**format:** `video_script`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

HTML es un lenguaje de marcado que indica a los navegadores web cómo estructurar las páginas que visitamos.

### Evidencia — chunks_used

#### `FE-ES-001_CH_002`

```text
## ¿Qué es HTML?

HTML (HyperText Markup Language, por sus siglas en inglés) es un lenguaje de marcado que indica a los navegadores web cómo estructurar las páginas web que visita. Puede ser tan complicado o tan simple como el desarrollador web quiera que sea. HTML consiste en una serie de elementos, que utiliza para encerrar, envolver o marcar diferentes partes del contenido para que aparezca o actúe de cierta manera. Las etiquetas pueden convertir el contenido en un hipervínculo para conectarse a otra página, poner palabras en cursiva, etc.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 14. ATOM-V1-014 — CAL-V1-015

**source_claim_id:** `card_1_back_claim_1`

**format:** `flashcards`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

Funciones y eventos; y bucles; condicionales.

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

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 15. ATOM-V1-015 — CAL-V1-017

**source_claim_id:** `question_1_explanation_claim_1`

**format:** `quiz`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

El documento define Kubernetes como una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios.

### Evidencia — chunks_used

#### `CLD-ES-001_CH_001`

```text
# ¿Qué es Kubernetes?

Esta página ofrece una visión general sobre Kubernetes.

Kubernetes es una plataforma portable y extensible de código abierto para administrar cargas de trabajo y servicios. Kubernetes facilita la automatización y la configuración declarativa. Tiene un ecosistema grande y en rápido crecimiento. El soporte, las herramientas y los servicios para Kubernetes están ampliamente disponibles.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---

## 16. ATOM-V1-016 — CAL-V1-019

**source_claim_id:** `key_point_2_claim_1`

**format:** `tldr`

**human_support_label:** `supported`

**selection_reason:** `supported_control`

### Source claim

La sección también presenta opciones para comenzar con Azure.

### Evidencia — chunks_used

#### `CLD-ES-002_CH_003`

```text
## Requisitos previos

- Conocimientos básicos sobre los términos y conceptos de TI

## Introducción a Azure

Elija la cuenta de Azure adecuada para usted. Pague a medida que habla o pruebe Azure gratis durante 30 días. Regístrese.

## Módulos en esta ruta de aprendizaje

En este módulo se presenta la informática en la nube. Trata aspectos como los conceptos de la nube, los modelos de implementación y la comprensión de la responsabilidad compartida en la nube.

En este módulo se presentan las ventajas que la informática en la nube puede ofrecerle a usted o su organización.
```

### Ground truth de atomización

**atomization_class:** `PENDING`

**atom_count:** `PENDING`

#### Atom 1

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 2

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 3

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

#### Atom 4

**atom_text:** PENDING

**atom_type:** `PENDING`

**expected_support:** `PENDING`

**review_notes:** PENDING

---
