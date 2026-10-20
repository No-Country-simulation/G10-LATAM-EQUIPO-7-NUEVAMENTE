# Content Support — Claim Atomization v1

## Estado

Experimental.

Este diseño no modifica todavía:

- `/evaluate/v2`
- `SemanticEvaluator`
- `quality_evaluator.py`
- el contrato Data/IA–Backend
- el cálculo productivo de `verdict`

Su objetivo es validar si una atomización más fina mejora la detección
de afirmaciones parcialmente respaldadas o de relaciones no respaldadas.

---

## 1. Problema

La evaluación de `content_support` v1 trabaja con claims factuales que
pueden contener más de una proposición.

Un claim puede mezclar:

- hechos respaldados;
- calificadores;
- relaciones temporales;
- relaciones causales;
- negaciones;
- condiciones;
- comparaciones;
- afirmaciones adicionales no respaldadas.

Esto puede provocar que un evaluador acepte el claim completo porque
encuentra evidencia para su proposición principal, aunque una parte
secundaria no esté respaldada.

Ejemplo observado:

> Antes de eso, la serie enseña conceptos básicos de la nube.

La evidencia respalda:

> La serie enseña conceptos básicos de la nube.

Pero no respalda:

> Eso ocurre antes del evento o contexto referido.

El claim original fue clasificado como `unsupported` por ground truth,
pero fue aceptado tanto por el router léxico como por el evaluador
semántico.

---

## 2. Evidencia experimental

Ground truth claim-level:

- 59 claims factuales anotados;
- 48 `supported`;
- 8 `unsupported`;
- 3 `uncertain`.

Entre los 8 claims `unsupported`:

- `atomic_unsupported`: 4
- `mixed_compound`: 1
- `relation_unsupported`: 3
- `unclear_segmentation`: 0

Resultado:

- 4 de 8 claims unsupported son estructuralmente descomponibles;
- tasa de descomposición observada: `0.5000`.

Esto sugiere que la atomicidad del claim es una variable relevante para
`content_support`.

---

## 3. Objetivo

Transformar una unidad factual potencialmente compuesta en una colección
de afirmaciones mínimas evaluables de forma independiente.

La atomización debe preservar el significado original.

No debe:

- inventar información;
- ampliar el claim;
- introducir conocimiento externo;
- cambiar afirmaciones por otras más fáciles de verificar;
- eliminar calificadores relevantes.

---

## 4. Entrada

Cada unidad de atomización recibe:

```json
{
  "source_claim_id": "scene_2_narration_claim_1",
  "claim_text": "Antes de eso, la serie enseña conceptos básicos de la nube.",
  "format": "video_script"
}
```

Opcionalmente puede conservarse información estructural:

```json
{
  "calibration_id": "CAL-V1-020",
  "document_id": "CLD-ES-002",
  "source_path": "scenes[1].narration"
}
```

`chunks_used` no son necesarios para atomizar.

La atomización analiza estructura lingüística, no soporte factual.

---

## 5. Salida

La salida debe conservar trazabilidad hacia el claim original.

Ejemplo:

```json
{
  "source_claim_id": "scene_2_narration_claim_1",
  "source_claim_text": "Antes de eso, la serie enseña conceptos básicos de la nube.",
  "atomization_status": "success",
  "atoms": [
    {
      "atom_id": "scene_2_narration_claim_1_atom_1",
      "text": "La serie enseña conceptos básicos de la nube.",
      "atom_type": "factual_proposition"
    },
    {
      "atom_id": "scene_2_narration_claim_1_atom_2",
      "text": "La enseñanza de conceptos básicos de la nube ocurre antes del evento o contexto referido.",
      "atom_type": "temporal_relation"
    }
  ]
}
```

---

## 6. Tipos de átomo

### `factual_proposition`

Afirmación factual independiente.

Ejemplo:

> La serie enseña conceptos básicos de la nube.

### `temporal_relation`

Relación temporal que forma parte del significado factual.

Indicadores posibles:

- antes;
- después;
- posteriormente;
- previamente;
- luego;
- otra vez;
- vuelve a.

Ejemplo:

> La enseñanza ocurre antes del evento referido.

### `causal_relation`

Relación de causa o consecuencia.

Indicadores posibles:

- porque;
- por eso;
- debido a;
- provoca;
- produce;
- permite;
- hace que.

### `conditional_relation`

Afirmación condicionada.

Indicadores posibles:

- si;
- cuando;
- siempre que;
- únicamente si;
- en caso de.

### `comparative_relation`

Comparación factual.

Indicadores posibles:

- más que;
- menos que;
- mejor que;
- mayor;
- menor;
- igual que.

### `negation_or_absence`

Negación o afirmación de ausencia.

Ejemplos:

> No existe una secuencia clara.

> No requiere supervisión humana.

### `scope_or_quantifier`

Calificadores que modifican el alcance factual.

Ejemplos:

- todos;
- ninguno;
- automáticamente;
- siempre;
- únicamente;
- por defecto;
- completamente.

Un cuantificador relevante no debe descartarse durante la atomización.

---

## 7. Principios de atomización

### 7.1 Preservar significado

La suma de los átomos debe representar el contenido factual del claim
original.

### 7.2 No eliminar relaciones

Una relación temporal, causal, condicional o comparativa puede ser la
parte no respaldada.

No debe desaparecer al simplificar el claim.

### 7.3 No atomizar por longitud

Una oración larga puede contener una sola proposición.

Una oración corta puede contener:

- hecho;
- relación;
- cuantificador.

La atomización debe basarse en semántica y estructura.

### 7.4 Evitar fragmentos sin significado

No producir átomos como:

```text
Antes de eso.
```

Debe reconstruirse la relación completa:

```text
La enseñanza ocurre antes del evento referido.
```

### 7.5 Mantener calificadores

Ejemplo:

```text
Kubernetes cifra automáticamente todo el tráfico por defecto.
```

No debe convertirse en:

```text
Kubernetes cifra tráfico.
```

porque se perderían:

- `automáticamente`;
- `todo`;
- `por defecto`.

Estos términos forman parte de la afirmación factual evaluada.

---

## 8. Agregación futura de soporte

Cada átomo podrá recibir:

```text
supported
unsupported
uncertain
```

El claim original podrá agregarse inicialmente con una regla conservadora:

```text
si algún átomo factual relevante = unsupported
→ claim = unsupported

si ningún átomo = unsupported
y algún átomo = uncertain
→ claim = uncertain

si todos los átomos = supported
→ claim = supported
```

Esta regla es experimental y deberá validarse antes de producción.

---

## 9. Ejemplos observados

### CAL-V1-015

Claim:

> Bloques fundamentales, los mismos cuatro, sin una secuencia clara.

Atomización:

1. Los cuatro elementos mencionados son bloques fundamentales.
2. Los cuatro bloques no tienen una secuencia clara.

Ground truth:

```text
atom_1 = supported
atom_2 = unsupported
```

Tipo:

```text
mixed_compound
```

### CAL-V1-016

Claim:

> El paradigma dirigido por eventos desacopla la ocurrencia notificable
> de la lógica reactiva que procesa dicha señal.

Atomización:

1. Los eventos son ocurrencias reportadas por el sistema.
2. El sistema permite responder a esas ocurrencias.
3. El paradigma dirigido por eventos desacopla la ocurrencia de la lógica reactiva.

Ground truth:

```text
atom_1 = supported
atom_2 = supported
atom_3 = unsupported
```

Tipo:

```text
relation_unsupported
```

### CAL-V1-020 — caso crítico

Claim:

> Antes de eso, la serie enseña conceptos básicos de la nube.

Atomización:

1. La serie enseña conceptos básicos de la nube.
2. La enseñanza de esos conceptos ocurre antes del evento o contexto referido.

Ground truth:

```text
atom_1 = supported
atom_2 = unsupported
```

Este claim produjo:

```text
legacy = supported
semantic = supported
human GT = unsupported
```

Por tanto es el caso principal que motiva Claim Atomization v1.

---

## 10. Esquema experimental propuesto

```python
from typing import Literal

from pydantic import BaseModel


AtomType = Literal[
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
]


AtomizationStatus = Literal[
    "success",
    "failed",
]


class AtomicClaim(BaseModel):
    atom_id: str
    text: str
    atom_type: AtomType


class ClaimAtomizationResult(BaseModel):
    source_claim_id: str
    source_claim_text: str
    atomization_status: AtomizationStatus
    atoms: list[AtomicClaim]
    error_message: str | None = None
```

---

## 11. Pipeline experimental propuesto

```text
generated_content
        ↓
structured factual extraction
        ↓
source claim
        ↓
Claim Atomizer
        ↓
atomic claims
        ↓
semantic content-support evaluator
        ↓
supported / unsupported / uncertain
        ↓
claim-level aggregation
        ↓
document-level content_support
```

---

## 12. Papel del router léxico

Los resultados actuales no justifican usar el router léxico como gate
de autoaceptación.

Sobre los claims binarios evaluables:

```text
legacy:
TP = 7
FP = 25
FN = 1
TN = 23

recall = 0.875
```

El router léxico puede conservarse experimentalmente para:

- diagnóstico;
- priorización;
- observabilidad;
- comparación histórica;
- análisis de costo.

Pero:

```text
legacy_needs_review = False
```

no debe equivaler automáticamente a:

```text
content_support = supported
```

---

## 13. Papel del evaluador semántico

El evaluador semántico mejora considerablemente la especificidad respecto
del router léxico.

Sin embargo también produjo un falso negativo en:

```text
CAL-V1-020
scene_2_narration_claim_1
```

El modelo verificó la proposición principal:

> La serie enseña conceptos básicos de la nube.

pero omitió evaluar adecuadamente:

> Antes de eso.

Por tanto, el uso de Gemini por sí solo tampoco elimina el problema de
claims compuestos.

---

## 14. Hipótesis de Claim Atomization v1

La hipótesis experimental es:

> Dividir claims compuestos en proposiciones y relaciones factuales
> mínimas antes de evaluar soporte reducirá falsos negativos causados por
> evidencia parcial dentro de una misma oración.

La hipótesis todavía debe validarse experimentalmente.

---

## 15. Criterio de éxito

Claim Atomization v1 se considerará prometedor si:

1. identifica correctamente relaciones relevantes en los casos
   `mixed_compound` y `relation_unsupported`;
2. no elimina calificadores relevantes;
3. no inventa nuevas afirmaciones;
4. conserva trazabilidad al claim original;
5. permite detectar como `unsupported` el componente temporal de
   `CAL-V1-020 scene_2_narration_claim_1`;
6. no degrada de forma significativa los claims completamente `supported`.

---

## 16. Próxima validación

Antes de cualquier integración productiva:

1. construir un dataset de atomización;
2. incluir claims `supported` y `unsupported`;
3. generar atomizaciones esperadas manuales;
4. probar un atomizador experimental;
5. evaluar:
   - exactitud de descomposición;
   - pérdida de significado;
   - creación de información nueva;
   - detección de relaciones;
6. ejecutar evaluación semántica sobre átomos;
7. comparar con el baseline claim-level actual.

---

## 17. Estado de decisión

Actualmente:

```text
Claim Atomization v1
status = experimental
production_integration = no
```

No se modifica `/evaluate/v2` hasta completar la validación experimental.