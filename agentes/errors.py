"""
Errores estructurados de la API de agentes.

Cada fallo (de Gemini o interno) se normaliza a un objeto con esta forma:

    {
        "code": "RESOURCE_EXHAUSTED",   # causa normalizada (ver CATALOGO)
        "message": "...",               # detalle corto y legible
        "retryable": true,              # ¿tiene sentido reintentar más tarde?
        "http_status": 429,             # HTTP que la API emite si TODO falla por esta causa
        "upstream_status": 429,         # HTTP que devolvió Gemini (None si no aplica)
        "provider": "gemini"            # "gemini" | "internal"
    }

Política HTTP global (ver evaluar_resultado_global):

    - Todo OK                          -> 200
    - Al menos una unidad OK y otra no -> 207 (fallo parcial controlado, no hay fail fast)
    - Todo falló                       -> HTTP de la causa dominante (429, 503, 504, 502, 404...)

Una "unidad" es la extracción de learning_metadata o cada formato solicitado.
"""
from typing import Dict, List, Optional, Tuple

from google.genai import errors as genai_errors

# HTTP para el éxito parcial. Si el backend prefiere un 200 con overall_status="partial",
# cambia este valor a 200 y no hay que tocar nada más.
PARTIAL_SUCCESS_HTTP_STATUS = 207

# El ORDEN de este diccionario es la prioridad cuando todo falla por causas distintas:
# se emite el HTTP de la primera causa que aparezca.
CATALOGO: Dict[str, Dict] = {
    "RESOURCE_EXHAUSTED":        {"http": 429, "retryable": True,  "provider": True},   # cuota / rate limit
    "PROVIDER_UNAVAILABLE":      {"http": 503, "retryable": True,  "provider": True},   # modelo saturado
    "PROVIDER_TIMEOUT":          {"http": 504, "retryable": True,  "provider": True},
    "PROVIDER_ERROR":            {"http": 502, "retryable": True,  "provider": True},   # 500/502 de Gemini
    "INVALID_MODEL_OUTPUT":      {"http": 502, "retryable": True,  "provider": True},   # vacío / no cumple schema
    "PROVIDER_REJECTED_REQUEST": {"http": 502, "retryable": False, "provider": True},   # 400 de Gemini
    "PROVIDER_AUTH_ERROR":       {"http": 500, "retryable": False, "provider": True},   # key inválida / sin permisos
    "MODEL_NOT_FOUND":           {"http": 500, "retryable": False, "provider": True},   # GEMINI_MODEL inexistente
    "NO_CONTEXT":                {"http": 404, "retryable": False, "provider": False},  # document_id sin contenido
    "UNSUPPORTED_FORMAT":        {"http": 422, "retryable": False, "provider": False},
    "INTERNAL_ERROR":            {"http": 500, "retryable": False, "provider": False},
}

PRIORIDAD: List[str] = list(CATALOGO.keys())

_MAX_MENSAJE = 300


class InvalidModelOutputError(Exception):
    """Gemini respondió, pero la salida está vacía o no cumple el schema esperado."""


def _recortar(texto: str) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= _MAX_MENSAJE else texto[: _MAX_MENSAJE - 3] + "..."


def build_error(code: str, message: str, upstream_status: Optional[int] = None) -> Dict:
    """Construye el objeto de error estructurado a partir de un código del catálogo."""
    if code not in CATALOGO:
        code = "INTERNAL_ERROR"
    info = CATALOGO[code]
    return {
        "code": code,
        "message": _recortar(message),
        "retryable": info["retryable"],
        "http_status": info["http"],
        "upstream_status": upstream_status,
        "provider": "gemini" if info["provider"] else "internal",
    }


def classify_exception(exc: BaseException) -> Dict:
    """Traduce cualquier excepción (SDK de Gemini u otra) a un error estructurado."""
    detalle = f"{type(exc).__name__}: {exc}"

    if isinstance(exc, InvalidModelOutputError):
        return build_error("INVALID_MODEL_OUTPUT", detalle)

    if isinstance(exc, genai_errors.APIError):
        codigo = getattr(exc, "code", None)
        estado = str(getattr(exc, "status", "") or "").upper()
        texto = str(exc)

        if codigo == 429 or estado == "RESOURCE_EXHAUSTED":
            causa = "RESOURCE_EXHAUSTED"
        elif codigo == 503 or estado == "UNAVAILABLE":
            causa = "PROVIDER_UNAVAILABLE"
        elif codigo == 504 or estado == "DEADLINE_EXCEEDED":
            causa = "PROVIDER_TIMEOUT"
        elif codigo in (500, 502) or estado == "INTERNAL":
            causa = "PROVIDER_ERROR"
        elif codigo in (401, 403) or "API_KEY_INVALID" in texto or "API key not valid" in texto:
            causa = "PROVIDER_AUTH_ERROR"
        elif codigo == 404:
            causa = "MODEL_NOT_FOUND"
        else:
            causa = "PROVIDER_REJECTED_REQUEST"
        return build_error(causa, detalle, upstream_status=codigo)

    nombre = type(exc).__name__.lower()
    if "timeout" in nombre:
        return build_error("PROVIDER_TIMEOUT", detalle)
    if "connect" in nombre:
        return build_error("PROVIDER_UNAVAILABLE", detalle)

    return build_error("INTERNAL_ERROR", detalle)


def resolver_http_global(errores: List[Dict]) -> int:
    """HTTP de la causa dominante cuando TODAS las unidades fallaron."""
    codigos = {e["code"] for e in errores if e}
    for causa in PRIORIDAD:
        if causa in codigos:
            return CATALOGO[causa]["http"]
    return 500


def evaluar_resultado_global(exitosas: int, errores: List[Dict]) -> Tuple[str, int]:
    """
    Devuelve (overall_status, http_status).

        sin errores                 -> ("success", 200)
        con éxitos y con errores    -> ("partial", PARTIAL_SUCCESS_HTTP_STATUS)
        solo errores                -> ("failed",  HTTP de la causa dominante)
    """
    if not errores:
        return "success", 200
    if exitosas > 0:
        return "partial", PARTIAL_SUCCESS_HTTP_STATUS
    return "failed", resolver_http_global(errores)


# ----------------------------------------------------------------------
# Evaluación de retrieval (contrato v2.0 de Data, ver rag/contract.py)
# ----------------------------------------------------------------------
# Los códigos de error son los de RetrieverService.retrieve_for_evaluation y NO se renombran.
EVAL_ERROR_HTTP: Dict[str, int] = {"INVALID_INPUT": 422, "RETRIEVAL_FAILED": 500}

# True : status="error" también se refleja en el HTTP (422 / 500), con el MISMO body del contrato.
# False: siempre 200 y el error viaja solo en el body (usar si el cliente de Data descarta
#        el body cuando recibe 4xx/5xx o 207).
EVAL_ERRORS_AS_HTTP = True


def http_evaluacion_caso(payload: Dict) -> int:
    """HTTP de un caso individual: 200 para success y no_results (un caso sin resultados es un dato)."""
    if payload.get("status") != "error" or not EVAL_ERRORS_AS_HTTP:
        return 200
    codigo = (payload.get("error") or {}).get("code")
    return EVAL_ERROR_HTTP.get(codigo, 500)


def evaluar_lote_evaluacion(payloads: List[Dict]) -> Tuple[str, int]:
    """
    Devuelve (overall_status, http_status) para un lote de casos.

        ningún error                  -> ("success", 200)
        errores y casos sin error     -> ("partial", 207)
        todos con error               -> ("failed", HTTP más grave: 500 antes que 422)

    Con EVAL_ERRORS_AS_HTTP=False el HTTP es siempre 200.
    """
    con_error = [p for p in payloads if p.get("status") == "error"]
    if not con_error:
        return "success", 200
    hay_exitos = len(con_error) < len(payloads)
    estado = "partial" if hay_exitos else "failed"
    if not EVAL_ERRORS_AS_HTTP:
        return estado, 200
    if hay_exitos:
        return estado, PARTIAL_SUCCESS_HTTP_STATUS
    codigos = {(p.get("error") or {}).get("code") for p in con_error}
    return estado, max(EVAL_ERROR_HTTP.get(c, 500) for c in codigos)
