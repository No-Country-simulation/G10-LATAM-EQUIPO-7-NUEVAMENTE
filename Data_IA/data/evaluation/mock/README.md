# Mock files — Data/IA Evaluation

Esta carpeta contiene archivos JSON de prueba utilizados por el área de Data/IA para validar contratos, flujos de evaluación y manejo de errores antes de integrar completamente los servicios reales de Agentes.

Los mocks se dividen actualmente en dos grupos:

1. **Retrieval Contract v1**
2. **Format Evaluation v1**

---

## 1. Retrieval Contract v1

Estos archivos permiten desarrollar y probar `02_data_ai_retrieval_evaluation_v1.ipynb` y los componentes asociados al contrato de retrieval.

### Archivos

- `retrieval_success_v1.json`: respuesta correcta con resultados.
- `retrieval_no_results_v1.json`: retrieval correcto sin resultados.
- `retrieval_error_v1.json`: fallo técnico del retrieval.

### Uso

Sirven para probar:

- validación del contrato de retrieval;
- manejo de estados;
- lectura de `rank`, `chunk_id`, `document_id`, `score` y `text`;
- manejo de errores;
- estructura del flujo de evaluación de retrieval.

Los scores y textos de estos mocks son ilustrativos y no representan resultados reales del modelo de Agentes.

---

## 2. Format Evaluation v1

Estos archivos permiten validar el contrato de evaluación de contenido generado para Sprint 2 antes de integrar completamente la lógica del evaluator en el endpoint `POST /evaluate`.

Actualmente los formatos soportados son:

- `quiz`
- `flashcards`

El contrato de evaluación utiliza:

- `document_id`;
- `format`;
- `generation_context`;
- `generated_content`;
- `chunks_used`.

---

### Contexto de generación

El campo `generation_context` conserva el contexto utilizado por Agentes durante la generación del contenido y sirve como referencia para evaluar posteriormente la adaptación didáctica.

Actualmente contiene:

- `profile`: perfil objetivo utilizado durante la generación;
- `niche`: área, dominio o nicho del contenido;
- `detail_level`: nivel de profundidad solicitado;
- `learning_objective`: objetivo de aprendizaje, opcional.

Los campos `profile`, `niche` y `detail_level` son obligatorios.

`learning_objective` puede omitirse y será interpretado como `None`.

Ejemplo:

```json
{
  "generation_context": {
    "profile": "student",
    "niche": "technology",
    "detail_level": "beginner",
    "learning_objective": "Comprender conceptos básicos de FastAPI"
  }
}
```

---

### Contenido generado

El campo `generated_content` se valida según el valor de `format`.

#### Quiz

Cuando:

```json
{
  "format": "quiz"
}
```

el contenido debe cumplir la estructura `QuizContent`.

Cada pregunta incluye:

- `question_id`;
- `question`;
- `options`;
- `correct_answer`;
- `explanation`.

Además se valida que:

- los `question_id` sean únicos;
- las opciones no estén vacías;
- las opciones no estén duplicadas;
- `correct_answer` coincida con una de las opciones.

Ejemplo de estructura:

```json
{
  "generated_content": {
    "title": "Quiz sobre FastAPI",
    "instructions": "Selecciona la respuesta correcta.",
    "questions": [
      {
        "question_id": "Q1",
        "question": "¿Qué clase se utiliza para crear una aplicación FastAPI?",
        "options": [
          "FastAPI",
          "Flask",
          "Django"
        ],
        "correct_answer": "FastAPI",
        "explanation": "La clase FastAPI se utiliza para crear la aplicación."
      }
    ]
  }
}
```

#### Flashcards

Cuando:

```json
{
  "format": "flashcards"
}
```

el contenido debe cumplir la estructura `FlashcardsContent`.

Cada flashcard incluye:

- `card_id`;
- `front`;
- `back`.

Además se valida que:

- los `card_id` sean únicos;
- `front` y `back` no sean idénticos.

Ejemplo de estructura:

```json
{
  "generated_content": {
    "title": "Flashcards sobre FastAPI",
    "instructions": "Intenta responder antes de revisar el reverso.",
    "cards": [
      {
        "card_id": "F1",
        "front": "¿Qué clase se usa para crear una aplicación FastAPI?",
        "back": "FastAPI"
      }
    ]
  }
}
```

---

### Evidencia utilizada

El campo `chunks_used` contiene la evidencia utilizada durante la generación.

Cada chunk incluye:

- `chunk_id`;
- `document_id`;
- `rank`;
- `score`;
- `text`.

Ejemplo:

```json
{
  "chunks_used": [
    {
      "chunk_id": "DOC-001_CH_001",
      "document_id": "DOC-001",
      "rank": 1,
      "score": 0.91,
      "text": "Para crear una aplicación se importa FastAPI desde el paquete fastapi y se instancia la clase FastAPI."
    }
  ]
}
```

Se valida que:

- los `chunk_id` sean únicos;
- los `rank` sean únicos;
- todos los chunks pertenezcan al mismo `document_id` de la solicitud.

Esta estructura permite conservar la evidencia exacta utilizada durante la generación y posteriormente evaluar si el contenido generado está respaldado por las fuentes recuperadas.

---

### Archivos válidos

- `evaluation_quiz_valid_v1.json`: ejemplo válido de evaluación para formato Quiz.
- `evaluation_flashcards_valid_v1.json`: ejemplo válido de evaluación para formato Flashcards.

---

### Archivos inválidos

- `evaluation_quiz_invalid_answer_v1.json`: Quiz inválido porque `correct_answer` no está incluida en `options`.
- `evaluation_flashcards_invalid_duplicate_id_v1.json`: Flashcards inválidas porque contiene `card_id` duplicados.
- `evaluation_invalid_chunk_document_v1.json`: solicitud inválida porque uno de los chunks pertenece a un `document_id` diferente al documento evaluado.

---

### Uso

Estos mocks permiten probar:

- validación de `QuizContent`;
- validación de `FlashcardsContent`;
- discriminación del schema mediante `format`;
- validación de `generation_context`;
- obligatoriedad de `profile`, `niche` y `detail_level`;
- carácter opcional de `learning_objective`;
- campos obligatorios y tipos de datos;
- IDs únicos en preguntas y flashcards;
- consistencia entre `correct_answer` y `options`;
- consistencia entre `document_id` y `chunks_used`;
- estructura completa de la evidencia utilizada;
- validación previa a la integración completa del endpoint `POST /evaluate`.

---

## Alcance actual

Los mocks de evaluación de formatos corresponden al alcance actual de Sprint 2, centrado en:

- Quiz;
- Flashcards;
- validación estructural del JSON;
- contexto utilizado durante la generación;
- evidencia utilizada por Agentes;
- preparación del servicio de evaluación de Data/IA.

La evaluación de calidad se integrará sobre este contrato utilizando las dimensiones:

- relevancia;
- coherencia;
- adaptación didáctica;
- información respaldada.

La lógica final del evaluator utilizará:

- `generated_content`;
- `generation_context`;
- `chunks_used`.

Estas entradas permitirán producir posteriormente una respuesta estructurada con:

- `status`;
- `scores`;
- `informacion_no_respaldada`;
- `observaciones`.

---

## Nota

Los contenidos, scores y chunks incluidos en estos archivos son datos de prueba.

No deben interpretarse como resultados reales del pipeline de Agentes ni como métricas finales del sistema.
