"""
Motor de evaluación de calidad algorítmica.
Analiza heurísticamente el texto generado contra los chunks y el contexto
para calcular puntajes reales sin depender de llamadas directas a LLMs.
"""
import json
from typing import Dict, Any, List, Tuple
from data_ai.schemas.format_evaluation import EvaluationScores

def evaluate(
    generated_content: Dict[str, Any],
    chunks_used: List[Dict[str, Any]],
    generation_context: Dict[str, Any]
) -> Tuple[EvaluationScores, bool]:
    """
    Calcula los 4 scores reales y detecta información no respaldada (alucinaciones).
    """
    # 1. Preparar los textos para el análisis (todo a minúsculas)
    content_text = json.dumps(generated_content, ensure_ascii=False).lower()
    chunks_text = " ".join([json.dumps(c, ensure_ascii=False).lower() for c in chunks_used])
    
    # 2. Relevancia (1-5): Qué tanto del 'learning_objective' o 'niche' está presente
    objetivo = generation_context.get("learning_objective", "").lower()
    nicho = generation_context.get("niche", "").lower()
    relevancia = 5 if (objetivo in content_text or nicho in content_text) else 3

    # 3. Coherencia (1-5): Verificación de estructura generada
    # Asumimos que si tiene llaves válidas y contenido sustancial, es coherente
    coherencia = 5 if len(generated_content.keys()) >= 1 and len(content_text) > 50 else 2

    # 4. Adaptación Didáctica (1-5): Cruce con el 'profile' y 'detail_level'
    perfil = generation_context.get("profile", "").lower()
    nivel_detalle = generation_context.get("detail_level", "").lower()
    adaptacion = 5
    
    # Regla: Si es principiante, el texto no debe ser abrumadoramente largo (heurística simple)
    if perfil == "principiante" and len(content_text) > 3000:
        adaptacion = 3
    elif nivel_detalle == "alto" and len(content_text) < 200:
        adaptacion = 2  # Penalizamos si pidieron alto detalle y es muy corto

    # 5. Información Respaldada y Detección de Alucinaciones
    # Extraemos palabras significativas del contenido generado (>5 letras)
    valores_generados = " ".join([str(v) for v in generated_content.values()]).lower()
    palabras_clave = [p for p in valores_generados.split() if len(p) > 5]
    
    # Contamos cuántas palabras clave NO están en los chunks de origen
    palabras_no_respaldadas = [p for p in palabras_clave if p not in chunks_text]
    
    # Si más del 25% del vocabulario significativo no existe en la fuente, es alucinación
    ratio_no_respaldado = len(palabras_no_respaldadas) / max(len(palabras_clave), 1)
    informacion_no_respaldada = ratio_no_respaldado > 0.25
    
    informacion_respaldada_score = 1 if informacion_no_respaldada else 5

    # 6. Ensamblar los resultados
    scores = EvaluationScores(
        relevancia=relevancia,
        coherencia=coherencia,
        adaptacion_didactica=adaptacion,
        informacion_respaldada=informacion_respaldada_score
    )

    return scores, informacion_no_respaldada