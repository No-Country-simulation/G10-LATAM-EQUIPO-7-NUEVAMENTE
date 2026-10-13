# Diagnóstico de calidad multiformato

Este diagnóstico reproduce la lógica léxica actual del evaluator
sobre los artefactos E2E ya generados. No vuelve a llamar a Gemini.

## Umbrales actuales

- Relevancia alta: `0.5`
- Relevancia media: `0.25`
- Alucinación/rechazo: `0.4`
- Respaldo excelente: `0.15`
- Respaldo bueno: `0.3`

## Resumen

| Fuente | Generado | Estado | Rel. reportada | Rel. recalculada | Ratio rel. | Respaldo reportado | Respaldo recalculado | Ratio no respaldado |
|---|---|---|---:|---:|---:|---:|---:|---:|
| MD | quiz | requiere_revision | 3 | 3 | 0.167 | 3 | 3 | 0.392 |
| MD | flashcards | requiere_revision | 3 | 3 | 0.000 | 5 | 5 | 0.130 |
| MD | tldr | rechazado | 4 | 4 | 0.333 | 1 | 1 | 0.457 |
| MD | video_script | rechazado | 3 | 3 | 0.000 | 1 | 1 | 0.404 |
| TXT | quiz | requiere_revision | 3 | 3 | 0.167 | 3 | 3 | 0.329 |
| TXT | flashcards | requiere_revision | 3 | 3 | 0.167 | 4 | 4 | 0.260 |
| TXT | tldr | rechazado | 4 | 4 | 0.333 | 1 | 1 | 0.526 |
| TXT | video_script | requiere_revision | 3 | 3 | 0.000 | 3 | 3 | 0.380 |
| PDF | quiz | requiere_revision | 3 | 3 | 0.167 | 4 | 4 | 0.200 |
| PDF | flashcards | requiere_revision | 3 | 3 | 0.000 | 4 | 4 | 0.186 |
| PDF | tldr | rechazado | 5 | 5 | 0.500 | 1 | 1 | 0.462 |
| PDF | video_script | rechazado | 4 | 4 | 0.333 | 1 | 1 | 0.495 |

## Cómo interpretar los archivos

- `quality_case_summary.csv`: una fila por combinación fuente/formato.
- `unsupported_terms.csv`: términos generados que no aparecen literalmente en los chunks recuperados.
- `relevance_terms.csv`: términos del contexto de generación y si aparecen literalmente en la salida.

Los términos `format_or_presentation_language` son vocabulario propio del formato.
Los `content_or_paraphrase_candidate` requieren revisión humana: pueden ser
paráfrasis válidas o información realmente no respaldada.

Este diagnóstico no modifica los umbrales ni el evaluator.
