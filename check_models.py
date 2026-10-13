"""
Diagnóstico de Gemini: valida la key del .env, lista los modelos disponibles
y prueba cuáles responden de verdad. No imprime la key completa.

Uso (desde la raíz del proyecto, con el .venv activo):
    python check_models.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

EXCLUIR = ("tts", "image", "embedding", "live", "audio", "imagen", "veo", "robotics", "computer-use", "aqa")
MAX_PRUEBAS = 10


def encontrar_env():
    base = Path(__file__).resolve().parent
    for carpeta in [base, *base.parents]:
        candidato = carpeta / ".env"
        if candidato.exists():
            return candidato
    return None


def main():
    env_path = encontrar_env()
    if env_path is None:
        sys.exit("No se encontró ningún archivo .env desde esta carpeta hacia arriba.")
    load_dotenv(dotenv_path=env_path, override=True)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    modelo_env = os.environ.get("GEMINI_MODEL", "").strip()

    print(f".env usado   : {env_path}")
    print(f"API key      : len={len(api_key)} | inicio={api_key[:4]} | fin={api_key[-4:]}")
    print(f"GEMINI_MODEL : {modelo_env or '(vacío)'}")

    if not api_key or api_key.startswith("fake"):
        sys.exit("\nLa key está vacía o es la falsa de pruebas. Revisa el .env.")

    try:
        http_options = types.HttpOptions(
            timeout=20_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        )
    except Exception:
        http_options = types.HttpOptions(timeout=20_000)

    client = genai.Client(api_key=api_key, http_options=http_options)

    # ---------- 1) Listar modelos ----------
    print("\n1) Listando modelos con tu key...")
    try:
        modelos = list(client.models.list())
    except genai_errors.APIError as e:
        sys.exit(f"   FALLÓ el listado: {e.code} {str(e)[:200]}\n   Si es 400/403, la key no es válida para esta API.")
    except Exception as e:
        sys.exit(f"   FALLÓ el listado: {type(e).__name__}: {str(e)[:200]}")

    def nombre(m):
        return (m.name or "").replace("models/", "")

    def soporta_generate(m):
        acciones = getattr(m, "supported_actions", None)
        return acciones is None or "generateContent" in acciones

    candidatos = sorted(
        n for n in (nombre(m) for m in modelos if soporta_generate(m))
        if n.startswith("gemini") and not any(x in n for x in EXCLUIR)
    )
    print(f"   {len(modelos)} modelos en total, {len(candidatos)} de texto para generateContent:")
    for n in candidatos:
        print(f"   - {n}")

    # ---------- 2) Probar modelos ----------
    a_probar = []
    if modelo_env:
        a_probar.append(modelo_env)
    for n in candidatos:
        if "flash" in n and n not in a_probar:
            a_probar.append(n)
    a_probar = a_probar[:MAX_PRUEBAS]

    print(f"\n2) Probando {len(a_probar)} modelo(s) con una llamada mínima (20 s máx. cada uno)...")
    funcionan = []
    for n in a_probar:
        marca = "  <- GEMINI_MODEL actual" if n == modelo_env else ""
        try:
            r = client.models.generate_content(model=n, contents="Responde solo con la palabra OK")
            texto = (r.text or "").strip()[:20]
            print(f"   OK   {n}{marca} -> {texto!r}")
            funcionan.append(n)
        except genai_errors.APIError as e:
            print(f"   {e.code}  {n}{marca} -> {str(e)[:140]}")
        except Exception as e:
            print(f"   ERR  {n}{marca} -> {type(e).__name__}: {str(e)[:140]}")

    # ---------- 3) Resultado ----------
    print("\n3) Resultado")
    if modelo_env and modelo_env in funcionan:
        print(f"   Tu GEMINI_MODEL ({modelo_env}) responde. La key y el modelo están bien.")
    elif funcionan:
        print("   Tu GEMINI_MODEL no respondió. Pon esto en el .env:")
        print(f"   GEMINI_MODEL={funcionan[0]}")
    else:
        print("   Ningún modelo respondió. Mira los códigos de arriba:")
        print("   503 = modelo saturado (existe, repite más tarde) | 429 = cuota | 404 = no existe para tu cuenta | 400/403 = key.")


if __name__ == "__main__":
    main()