# Incremento 3 — Integración del ciclo de revisión V2 (Sprint 4)

## Objetivo

Validar **sin servicios externos** el comportamiento conjunto de componentes reales de BackendAPI: servicios de aplicación, adaptadores HTTP para Agentes y Data/IA, persistencia SQLite, historial de revisiones, consulta de formatos vigentes y construcción del paquete educativo persistible.

Este incremento **solo incorpora pruebas y documentación**. No altera los contratos ni el comportamiento productivo. Es un commit independiente posterior a `40c7b9b` (orquestación) y `2a9e6280` (contrato V2).

## Componentes utilizados

| Responsabilidad | Implementación bajo prueba |
|---|---|
| Coordinación de generación y evaluación | `AdaptationOrchestrationService` |
| Decisión y límite de corrección | `FormatAutoRevisionService` |
| Solicitud a Agentes | `FormatRevisionService` y `HTTPAgentRevisionAdapter` |
| Evaluación pedagógica | `FormatEvaluationService` y `HTTPDataIAAdapter` |
| Persistencia documental, de formatos y evaluaciones | Repositorios SQLite reales con base temporal |
| Historial y consulta pública | `FormatRevisionHistoryService` y `GeneratedFormatQueryService` |
| Paquete educativo | `GeneratedPackageStorageService` con almacenamiento simulado |

La simulación solo sustituye las respuestas HTTP (`httpx.MockTransport`) y OCI (doble en memoria). Cada caso utiliza un archivo SQLite independiente mediante `tmp_path`.

## Casos cubiertos

1. Evaluación inicial `requires_revision` o `rejected` → una corrección exitosa → reevaluación `approved` → persistencia de ambas versiones → historial y snapshot con versión corregida.
2. Evaluación inicial `approved` o `verdict=null` → no invocar al revisor y conservar el original.
3. La reevaluación de la corrección devuelve nuevamente `rejected` → se registra sin generar una segunda corrección.
4. Agentes devuelve HTTP 503 con `status=failed` y error estructurado → conservar original, registrar revisión fallida y no reevaluar.
5. Agentes devuelve `revision_id` incorrecto, contenido inválido o timeout → cerrar la reserva como `failed`, sin ejecutar otra llamada.
6. Data/IA falla durante la reevaluación → conservar la revisión exitosa y **no inventar** una evaluación aprobada.
7. Un segundo procesamiento del mismo par (raíz, evaluación) no genera otra revisión ni otra llamada HTTP.

## Comandos

Desde la carpeta `backend`:

```powershell
python -m ruff check .
python -m pytest -q tests/integration/test_revision_flow_v2_sqlite.py
python -m pytest -q
git diff --check
```

## Límites y riesgos pendientes

- **No es una prueba E2E real:** los proveedores externos y OCI todavía están simulados. Agentes debe publicar `/api/v1/revise` con el contrato acordado y Data/IA debe estar desplegado.
- La política actual de snapshot prioriza el **último `success` técnico**, no el veredicto pedagógico `approved`. Así, una revisión con evaluación final `rejected` o sin reevaluación puede seguir siendo la versión vigente en OCI. **Se requiere una decisión de producto/QA antes de modificar esta política.**
- Una interrupción abrupta del proceso después de reservar `processing` sigue requiriendo una política de reconciliación. Corresponde al incremento 4; no se implementa ni simula recuperación en este commit.
- No se habilitan reintentos técnicos hasta contar con una garantía comprobada de idempotencia en Agentes por `revision_id`.
- `AUTO_REVISION_ENABLED=false` debe permanecer por defecto hasta terminar las pruebas con servicios reales.

## Criterios para crear el commit

- Ruff y Pytest completos en verde.
- `git diff --check` sin errores.
- Confirmar que **solo** se añaden este archivo y `tests/integration/test_revision_flow_v2_sqlite.py`.
- No incluir instaladores, ZIP ni archivos temporales en Git.

## Commit sugerido

`test(backend): valida integracion de revision V2 con SQLite y HTTP simulado`
