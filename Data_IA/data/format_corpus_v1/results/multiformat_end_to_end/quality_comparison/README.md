# Comparación experimental del evaluator de calidad

Compara la heurística léxica actual contra una variante experimental.
No modifica el evaluator de producción y no llama a Gemini.

## Variante experimental

- normaliza acentos;
- aplica singularización básica conservadora;
- evalúa una variante donde términos procedentes de `generation_context`
  pueden aceptarse durante el chequeo de respaldo;
- excluye vocabulario estructural/presentacional;
- para `video_script`, evalúa respaldo factual sobre `narration`;
- para `tldr`, excluye el título del chequeo factual.

> Nota: el uso de `generation_context` como fuente permitida para
> `informacion_respaldada` fue una estrategia experimental y no forma parte
> del Quality Evaluator V1.1 final. En la implementación final, el respaldo
> factual se evalúa exclusivamente contra `chunks_used`.

## Resultados

| Fuente | Formato | Reportado | Baseline | Mejorado | Ratio base | Ratio mejorado | Support base | Support mejorado |
|---|---|---|---|---|---:|---:|---:|---:|
| MD | quiz | requiere_revision | requiere_revision | requiere_revision | 0.392 | 0.196 | 3 | 4 |
| MD | flashcards | requiere_revision | requiere_revision | requiere_revision | 0.130 | 0.093 | 5 | 5 |
| MD | tldr | rechazado | rechazado | aprobado | 0.457 | 0.294 | 1 | 4 |
| MD | video_script | rechazado | rechazado | requiere_revision | 0.404 | 0.109 | 1 | 5 |
| TXT | quiz | requiere_revision | requiere_revision | requiere_revision | 0.329 | 0.264 | 3 | 4 |
| TXT | flashcards | requiere_revision | requiere_revision | aprobado | 0.260 | 0.225 | 4 | 4 |
| TXT | tldr | rechazado | rechazado | rechazado | 0.526 | 0.458 | 1 | 1 |
| TXT | video_script | requiere_revision | requiere_revision | requiere_revision | 0.380 | 0.242 | 3 | 4 |
| PDF | quiz | requiere_revision | requiere_revision | requiere_revision | 0.200 | 0.203 | 4 | 4 |
| PDF | flashcards | requiere_revision | requiere_revision | requiere_revision | 0.186 | 0.176 | 4 | 4 |
| PDF | tldr | rechazado | rechazado | requiere_revision | 0.462 | 0.308 | 1 | 3 |
| PDF | video_script | rechazado | rechazado | requiere_revision | 0.495 | 0.281 | 1 | 4 |

## Interpretación

El baseline debe coincidir con el evaluator actual. Si no coincide,
la comparación no debe usarse para proponer cambios.

Una mejora es prometedora si reduce falsos positivos sin convertir
automáticamente todos los casos en aprobados.
