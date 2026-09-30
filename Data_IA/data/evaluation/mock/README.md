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

Estos archivos permiten validar el contrato de evaluación de contenido generado para Sprint 2 antes de implementar e integrar el endpoint `POST /evaluate`.

Actualmente los formatos soportados son:

- `quiz`
- `flashcards`

El contrato de evaluación utiliza:

- `document_id`;
- `format`;
- `generated_content`;
- `chunks_used`.

### Archivos válidos

- `evaluation_quiz_valid_v1.json`: ejemplo válido de evaluación para formato Quiz.
- `evaluation_flashcards_valid_v1.json`: ejemplo válido de evaluación para formato Flashcards.

### Archivos inválidos

- `evaluation_quiz_invalid_answer_v1.json`: Quiz inválido porque `correct_answer` no está incluida en `options`.
- `evaluation_flashcards_invalid_duplicate_id_v1.json`: Flashcards inválidas porque contiene `card_id` duplicados.
- `evaluation_invalid_chunk_document_v1.json`: solicitud inválida porque uno de los chunks pertenece a un `document_id` diferente al documento evaluado.

### Uso

Estos mocks permiten probar:

- validación de `QuizContent`;
- validación de `FlashcardsContent`;
- discriminación del schema mediante `format`;
- campos obligatorios y tipos de datos;
- IDs únicos en preguntas y flashcards;
- consistencia entre `correct_answer` y `options`;
- consistencia entre `document_id` y `chunks_used`;
- validación previa a la implementación del endpoint `POST /evaluate`.

---

## Alcance actual

Los mocks de evaluación de formatos corresponden al alcance actual de Sprint 2, centrado en:

- Quiz;
- Flashcards;
- validación estructural del JSON;
- preparación del servicio de evaluación de Data/IA.

La evaluación de calidad —relevancia, coherencia, adaptación didáctica e información respaldada— se integrará sobre este contrato en las siguientes etapas del flujo.

---

## Nota

Los contenidos, scores y chunks incluidos en estos archivos son datos de prueba.

No deben interpretarse como resultados reales del pipeline de Agentes ni como métricas finales del sistema.
