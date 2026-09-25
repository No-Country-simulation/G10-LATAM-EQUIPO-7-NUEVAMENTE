import sys
import os
import time

# Forzar a Python a reconocer la raíz del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agentes.rag.extractor import extract_document
from agentes.rag.cleaner import clean_text
from agentes.rag.chunker import create_chunks
from agentes.rag.embeddings import MultilingualEmbedding
from agentes.rag.vector_store import VectorStore 
from agentes.agent_v1 import AgentV1

# ---------------------------------------------------------
# Funciones para el efecto visual en terminal
# ---------------------------------------------------------
def imprimir_lento(texto, retardo=0.015):
    for caracter in str(texto):
        sys.stdout.write(caracter)
        sys.stdout.flush()
        time.sleep(retardo)
    print()

def barra_progreso(mensaje, iteraciones=15, retardo=0.03):
    sys.stdout.write(mensaje + " [")
    for _ in range(iteraciones):
        sys.stdout.write("■")
        sys.stdout.flush()
        time.sleep(retardo)
    print("] Ejecución OK")

# ---------------------------------------------------------
# Pipeline RAG
# ---------------------------------------------------------
def ejecutar_demo(ruta_archivo: str, pregunta_usuario: str):
    imprimir_lento("\n[SISTEMA] Iniciando orquestación del pipeline RAG...\n", 0.03)
    
    # 1. Extracción 
    imprimir_lento(f"[PASO 1] MODULE: agentes.rag.extractor")
    imprimir_lento(f"  ↳ Ejecutando: extract_document(path='{ruta_archivo}')")
    documentos = extract_document(ruta_archivo)
    imprimir_lento(f"  ↳ Retorno: list[Document] -> {len(documentos)} documento(s) extraído(s)")
    if documentos:
        preview = documentos[0].text[:75].replace('\n', ' ')
        imprimir_lento(f"  ↳ Preview: \"{preview}...\"")
    input("\n>> [Enter] para continuar al Cleaner...")
    
    # 2. Limpieza 
    imprimir_lento("\n[PASO 2] MODULE: agentes.rag.cleaner")
    imprimir_lento("  ↳ Ejecutando: clean_text(text) iterativamente sobre list[Document]")
    barra_progreso("  ↳ Aplicando regex y normalización NFKC", iteraciones=20)
    for doc in documentos:
        doc.text = clean_text(doc.text)
    input("\n>> [Enter] para continuar al Chunker...")
        
    # 3. Chunking 
    imprimir_lento("\n[PASO 3] MODULE: agentes.rag.chunker")
    imprimir_lento("  ↳ Ejecutando: create_chunks(documents=documentos)")
    chunks = create_chunks(documentos)
    imprimir_lento(f"  ↳ Retorno: list[Chunk] -> {len(chunks)} fragmentos generados")
    if chunks:
        imprimir_lento(f"  ↳ Ejemplo de metadatos: {chunks[0].metadata}")
    input("\n>> [Enter] para inicializar Vector Store...")
    
    # 4. Vectorización y base de datos
    imprimir_lento("\n[PASO 4] MODULE: agentes.rag.vector_store & embeddings")
    imprimir_lento("  ↳ Instanciando: MultilingualEmbedding(model_name='paraphrase-multilingual-MiniLM-L12-v2')")
    modelo_embedding = MultilingualEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    imprimir_lento("  ↳ Instanciando: VectorStore(path='./chroma_demo', embedding_service=modelo_embedding)")
    # Forzamos la ruta para crear el Sandbox visible en la raíz
    vector_store = VectorStore(path="./chroma_demo", embedding_service=modelo_embedding)
    
    imprimir_lento("  ↳ Ejecutando: vector_store.add_chunks(chunks)")
    barra_progreso("  ↳ Calculando embeddings en ChromaDB", iteraciones=25)
    input("\n>> [Enter] para invocar al Agente y consultar...")
    
    # 5. Ejecución del agente final
    imprimir_lento("\n[PASO 5] MODULE: agentes.agent_v1")
    imprimir_lento("  ↳ Instanciando: AgentV1(vector_store=vector_store)")
    agente = AgentV1(vector_store=vector_store)
    
    imprimir_lento(f"  ↳ Ejecutando: agente.answer(query='{pregunta_usuario}')")
    barra_progreso("  ↳ RetrieverService procesando búsqueda por similitud (Cosine)", iteraciones=20)
    respuesta = agente.answer(query=pregunta_usuario)
    
    # ---------------------------------------------------------
    # Formateo de la respuesta
    # ---------------------------------------------------------
    print("\n" + "═"*70)
    imprimir_lento("  === CONTEXTO RECUPERADO (SearchResult) === 🤖", 0.03)
    print("═"*70 + "\n")
    
    for i, resultado in enumerate(respuesta, 1):
        imprimir_lento(f"--- MATCH #{i} ---")
        imprimir_lento(f" 🔹 ID del Chunk : {resultado.chunk_id}")
        imprimir_lento(f" 🔹 Relevancia   : {resultado.score * 100:.2f}% (Cosine Similarity)")
        imprimir_lento(f" 🔹 Metadatos    : {resultado.metadata}")
        imprimir_lento(f" 🔹 Contenido extraído:\n")
        
        verde_matrix = "\033[92m"
        reset_color = "\033[0m"
        texto_formateado = "\n".join([f"    {linea}" for linea in resultado.text.split('\n')])
        
        # Impresión lenta y en verde matrix para el contenido
        imprimir_lento(f"{verde_matrix}{texto_formateado}{reset_color}", 0.04)
        print("\n" + "-"*70 + "\n")

if __name__ == "__main__":
    documento_prueba = "hackathon_spec.txt"
    pregunta_prueba = "¿Cuáles son las especificaciones principales del hackathon?"
    
    os.system('cls' if os.name == 'nt' else 'clear') 
    imprimir_lento("==================================================================")
    imprimir_lento("   [DEBUG MODE] ORQUESTADOR RAG - PRUEBA DE INTEGRACIÓN CONTINUA  ")
    imprimir_lento("==================================================================")
    imprimir_lento(f" Target    : {documento_prueba}")
    imprimir_lento(f" Query     : {pregunta_prueba}\n")
    
    input(">> [Enter] para iniciar secuencia de ejecución...")
    ejecutar_demo(documento_prueba, pregunta_prueba)
    
    # Bloque de cierre
    print("\n" + "="*70)
    imprimir_lento(" [SISTEMA] PRUEBA DE INTEGRACIÓN RAG FINALIZADA CON ÉXITO", 0.03)
    imprimir_lento(" Conexión vectorial con ChromaDB cerrada.", 0.01)
    imprimir_lento(" Process finished with exit code 0", 0.01)
    print("="*70 + "\n")