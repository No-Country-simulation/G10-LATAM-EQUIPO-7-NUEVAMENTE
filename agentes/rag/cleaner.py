import unicodedata


def clean_text(text: str) -> str:
    """
    Limpieza conservadora (punto 9 del review).

    Solo normaliza codificación y saltos de línea. NO toca indentación,
    espacios internos ni hace strip() por línea, porque eso corrompe
    código, YAML u otro contenido técnico sensible al espaciado.

    NOTA: para el corpus congelado de Ground Truth v1 (chunks_v1.csv)
    esta función NO se aplica en absoluto — ver chunks_loader.py.
    Esto solo aplica al pipeline de ingestión de documentos nuevos.
    """

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    return text