import sys
import os
# Agregamos la raíz del proyecto al PYTHONPATH para que encuentre la carpeta 'agentes'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import os
import shutil
import sys
from sentence_transformers import SentenceTransformer
from agentes.rag.models import Chunk
from agentes.rag.vector_store import VectorStore 

class MultilingualEmbedding:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        embedding = self.model.encode(query, normalize_embeddings=True)
        return embedding.tolist()

def pausa():
    input("\n[Presione ENTER para continuar al siguiente paso...]")

def tipo_maquina(texto, velocidad=0.035):
    """Imprime el texto letra por letra de forma más pausada."""
    for letra in texto:
        sys.stdout.write(letra)
        sys.stdout.flush()
        time.sleep(velocidad)
    print()

def ejecutar_demo():
    print("\n" + "="*70)
    print(" INICIANDO DEMO: HACKATHON RAG PIPELINE - CONTRATO V1")
    print("="*70)
    pausa()

    # ---------------------------------------------------------
    print("\n[PASO 1] Leyendo documento crudo (hackathon_spec.txt)...")
    ruta_quemada = "../hackathon_spec.txt" # Apunta un nivel arriba hacia la raíz
    print(f"-> Ruta del archivo: {ruta_quemada}")
    
    if os.path.exists(ruta_quemada):
        with open(ruta_quemada, "r", encoding="utf-8") as f:
            texto = f.read()
    else:
        texto = "Especificación Técnica del Pipeline RAG - Hackathon Latam v1.0. El sistema implementa un servicio de recuperación estricto (RetrieverService) integrado con ChromaDB."
    
    print("\nContenido extraído del archivo:")
    tipo_maquina(f"   {texto[:150]}...\n", velocidad=0.025)
    pausa()

    # ---------------------------------------------------------
    print("\n[PASO 2] Procesando y empaquetando fragmentos (Chunks)...")
    textos_crudos = texto.split(".\n")
    chunks_preparados = []
    
    for i, txt in enumerate(textos_crudos):
        if txt.strip():
            print(f"   [SYSTEM] Procesando tensor para fragmento {i+1}...")
            time.sleep(0.4)
            nuevo_chunk = Chunk(
                id=f"demo_hackathon_{i}", 
                text=txt.strip() + ("." if not txt.endswith(".") else ""), 
                metadata={"source": "hackathon_spec.txt"}
            )
            chunks_preparados.append(nuevo_chunk)
            print(f"   [CHUNK {i+1}] Empaquetado exitoso con ID y Metadatos.")
            time.sleep(0.3)
    pausa()

    # ---------------------------------------------------------
    print("\n[PASO 3] Creacion de base de datos persistente desde cero...")
    db_path = "../chroma_demo_live" # Se crea en la raíz del proyecto
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
        print("-> [Limpieza] Directorio previo eliminado para demostracion en vivo.")
    
    print("-> Inicializando motor de embeddings (MultilingualEmbedding)...")
    embedding_service = MultilingualEmbedding(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    
    print("-> Instanciando VectorStore con ChromaDB PersistentClient...")
    vector_store = VectorStore(
        path=db_path,
        collection_name="demo_hackathon",
        embedding_service=embedding_service
    )
    
    print("-> Persistiendo chunks e indices vectoriales en disco...")
    vector_store.add_chunks(chunks_preparados)
    print(" [OK] Base de datos ChromaDB generada e indexada correctamente.")
    pausa()

    # ---------------------------------------------------------
    print("\n[PASO 4] Ejecutando busqueda semantica (Retrieval)...")
    pregunta = "¿Cómo deben estructurarse obligatoriamente las respuestas del agente según el Contrato v1?"
    print(f"-> Consulta de usuario: '{pregunta}'")
    print("-> Ejecutando calculo de similitud coseno en el espacio vectorial...")
    time.sleep(1.2)

    resultados = vector_store.search(query=pregunta, top_k=2)
    
    print("\n Resultados obtenidos por el motor RAG:")
    for i, res in enumerate(resultados):
        print(f"   [MATCH TOP {i+1}] Score de relevancia: {res.score:.4f}")
        print("   Texto recuperado:")
        tipo_maquina(f"      \"{res.text}\"", velocidad=0.035)
        print(f"   Metadatos: {res.metadata}\n")
    
    print("="*70)
    print(" DEMOSTRACION FINALIZADA CON EXITO")
    print("="*70 + "\n")

if __name__ == "__main__":
    ejecutar_demo()
    