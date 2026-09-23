# Mock files — Retrieval Contract v1

Estos archivos permiten desarrollar y probar `02_data_ai_retrieval_evaluation_v1.ipynb` antes de que el equipo de Agentes termine la implementación real del retrieval.

## Archivos

- `retrieval_success_v1.json`: respuesta correcta con resultados.
- `retrieval_no_results_v1.json`: retrieval correcto sin resultados.
- `retrieval_error_v1.json`: fallo técnico del retrieval.

## Uso

Sirven para probar:

- validación del contrato;
- manejo de estados;
- lectura de `rank`, `chunk_id`, `document_id`, `score` y `text`;
- manejo de errores;
- estructura del Notebook 02.

Los scores y textos de estos mocks son ilustrativos y no representan resultados reales del modelo de Agentes.
