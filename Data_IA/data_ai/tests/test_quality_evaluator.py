import pytest
from data_ai.evaluation.quality_evaluator import evaluate

def test_evaluacion_aprobada_quiz():
    # Contexto y chunks reales simulados
    context = {"learning_objective": "python", "profile": "avanzado", "detail_level": "medio"}
    chunks = [{"text": "python es un lenguaje de programacion excelente para backend"}]
    # JSON de salida generado
    content = {"pregunta_1": "que es python", "respuesta_1": "un lenguaje de programacion excelente"}
    
    scores, alucinacion = evaluate(content, chunks, context)
    
    assert scores.relevancia == 5
    assert scores.coherencia == 5
    assert scores.adaptacion_didactica == 5
    assert scores.informacion_respaldada == 5
    assert alucinacion is False

def test_evaluacion_requiere_revision_principiante():
    # Simulamos un usuario principiante
    context = {"learning_objective": "javascript", "profile": "principiante"}
    chunks = [{"text": "javascript es util para desarrollo web " * 100}] 
    # Generamos un texto enorme (>3000 chars) para disparar la regla de adaptación
    texto_largo = "javascript " * 400 
    content = {"flashcard_1": texto_largo}
    
    scores, alucinacion = evaluate(content, chunks, context)
    
    # La adaptación baja a 3 porque es demasiado texto para un principiante
    assert scores.adaptacion_didactica == 3 
    assert alucinacion is False

def test_evaluacion_rechazada_por_alucinacion_flashcards():
    context = {"learning_objective": "react", "niche": "frontend"}
    chunks = [{"text": "react es una libreria de interfaces"}]
    # Contenido con palabras largas inventadas que no están en la fuente
    content = {"tarjeta": "react permite construir naves espaciales mediante componentes intergalacticos"}
    
    scores, alucinacion = evaluate(content, chunks, context)
    
    # Detecta que más del 25% del vocabulario es inventado
    assert alucinacion is True
    assert scores.informacion_respaldada == 1