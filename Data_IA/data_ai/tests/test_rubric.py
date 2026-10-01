import pytest
from data_ai.schemas.format_evaluation import EvaluationScores
from data_ai.evaluation.rubric import calcular_veredicto_evaluacion

def test_aprobacion_exitosa():
    scores = EvaluationScores(relevancia=5, coherencia=4, adaptacion_didactica=4, informacion_respaldada=5)
    status, _ = calcular_veredicto_evaluacion(scores, False)
    assert status == "aprobado"

def test_rechazo_por_alucinacion():
    scores = EvaluationScores(relevancia=5, coherencia=5, adaptacion_didactica=5, informacion_respaldada=5)
    status, _ = calcular_veredicto_evaluacion(scores, True)
    assert status == "rechazado"

def test_rechazo_por_puntaje_critico():
    scores = EvaluationScores(relevancia=5, coherencia=4, adaptacion_didactica=2, informacion_respaldada=5)
    status, _ = calcular_veredicto_evaluacion(scores, False)
    assert status == "rechazado"

def test_requiere_revision_por_puntaje_regular():
    scores = EvaluationScores(relevancia=5, coherencia=3, adaptacion_didactica=4, informacion_respaldada=5)
    status, _ = calcular_veredicto_evaluacion(scores, False)
    assert status == "requiere_revision"