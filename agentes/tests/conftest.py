import os

# Configuración estricta de variables de prueba para la suite pytest.
# Esto previene errores de colección de módulos que leen os.environ a nivel raíz
# sin modificar el comportamiento estricto del código de producción.
os.environ.setdefault("GEMINI_API_KEY", "fake-test-key-for-pytest")
os.environ.setdefault("GEMINI_MODEL", "gemini-test-model")
