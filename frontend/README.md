# NuevaMente - Frontend

Este módulo corresponde al **Frontend** de la plataforma **NuevaMente** (Hackathon ONE · Grupo 10 · LATAM).
Desarrollado en **JavaScript moderno (ES6 Modules), HTML5 y CSS3**, sin frameworks ni paso de build, bajo principios de arquitectura limpia y Responsabilidad Única (SRP), con diseño Glassmorphism y modo oscuro fijo.

---

## Cómo Ejecutar el Frontend Localmente

Debido al uso de módulos nativos ES6 (`import` / `export`), los navegadores requieren que los archivos se sirvan a través de un servidor web local (no funciona abriendo `index.html` directo con `file://`, por restricciones de CORS del navegador).

Tienes cualquiera de estas 3 formas sencillas:

### Opción 1: Con Vite (Estándar recomendado)
Abre tu terminal en la carpeta `frontend` y ejecuta:
```bash
npm install
npm run dev
```
Vite iniciará el servidor de desarrollo en [http://localhost:3000](http://localhost:3000) con Hot Module Replacement (HMR).

### Opción 2: Con Python
Abre tu terminal en la carpeta `frontend` y ejecuta:
```bash
python -m http.server 3000
```

### Opción 3: Con la extensión Live Server de VS Code
1. Abre la carpeta `frontend` en Visual Studio Code.
2. Haz clic derecho sobre `index.html`.
3. Selecciona **"Open with Live Server"**.

### Conexión con Backend (FastAPI)

El Frontend está conectado exclusivamente al Backend real (FastAPI). La URL se desacopló completamente:
- Se configura en el archivo `.env` mediante `VITE_API_BASE_URL` (ver `.env.example`).
- Soporta configuración dinámica en caliente desde la interfaz haciendo clic en el badge **"Backend API"** del header.
- Por defecto apunta a `http://localhost:8000` con timeout de 30 segundos.

---

## Arquitectura Modular de Carpetas

```
frontend/
├── index.html                   # Orquestador de vistas SPA (Single Page Application)
├── README.md                    # Este documento
├── package.json                 # Scripts y dependencias de Vite.js
├── vite.config.js               # Configuración del servidor de desarrollo Vite
├── .env.example                 # Plantilla pública de variables de entorno
├── css/
│   ├── main.css                 # Importador central de hojas de estilo modulares
│   ├── variables.css            # Tokens de diseño, Glassmorphism y paleta dorada/cyan
│   ├── layout.css               # Header, navbar de pestañas principales y barra de estado
│   ├── components.css           # Botones, badges, inputs, chips y notificaciones toast
│   ├── bookshelf.css            # El Gran Librero 3D y el Cuaderno Abierto realista
│   ├── upload-tab.css           # Vista de Carga de Documento, stepper y panel de pruebas
│   ├── notebook.css             # Cuaderno Interactivo Dinámico (hojas, índice y lectura)
│   ├── study-hub.css            # Centro de Estudio (Flashcards, Quiz, Video, Resumen)
│   ├── portada.css              # Portada de bienvenida a pantalla completa
│   └── modals.css               # Modales de utilidad y diálogo de estado del Backend
└── js/
    ├── config.js                # Configuración desacoplada (Vite .env, runtime y límites)
    ├── state.js                 # Almacén de estado reactivo global (Store con Observable)
    ├── main.js                  # Punto de entrada y montaje de la aplicación
    ├── api/
    │   └── apiClient.js         # Cliente HTTP fetch hacia el Backend (FastAPI real)
    └── modules/
        ├── router.js            # Enrutador de pestañas (Biblioteca, Carga, Centro de Estudio)
        ├── portada.js           # Controlador de la portada de bienvenida y transición
        ├── bookshelf.js         # Controlador del Librero 3D y el Cuaderno Abierto
        ├── uploadTab.js         # Controlador de carga, parámetros y flujo real con el Backend
        ├── notifications.js     # Sistema de notificaciones toast (éxito, error, advertencia)
        ├── statusDialog.js      # Diálogo de estado tras cada respuesta del Backend
        ├── notebook.js          # Renderizador del Cuaderno dinámico
        ├── studyHub.js          # Orquestador del Centro de Estudio multi-formato
        ├── flashcards.js        # Lógica de Flashcards, volteo y atajos de teclado
        ├── quiz.js              # Lógica de Quiz interactivo con justificación pedagógica
        ├── videoGuide.js        # Guion didáctico y tutorial adaptativo
        └── summary.js           # Síntesis ejecutiva y términos clave
```

---

## Flujo y Experiencia de Usuario

1. **Portada de Bienvenida**
   Vista de pantalla completa con el logo del proyecto. Un clic transiciona a la biblioteca.

2. **La Biblioteca**
   Estantería de libros interactivos en 3D. Al hacer clic en cualquiera, se despliega un cuaderno abierto con el detalle del documento (tiempo de lectura, cantidad de secciones, nivel) y las opciones de estudio disponibles.

3. **Carga de Documento**
   Zona de arrastrar y soltar para PDF, Markdown o TXT (hasta 10 MB). Selector de parámetros de adaptación: perfil del estudiante, área temática y formato de salida. Al procesar, un panel muestra el avance en tiempo real contra el Backend y notifica el resultado (documento guardado, duplicado detectado, o cualquier error) mediante un diálogo de estado y notificaciones toast.

4. **Centro de Estudio**
   - **Flashcards**: tarjetas con animación de volteo y pistas pedagógicas.
   - **Quiz**: preguntas de autoevaluación con validación inmediata y justificación.
   - **Tutorial**: guion pedagógico estructurado con marcas de tiempo.
   - **Resumen**: síntesis ejecutiva con puntos clave y términos clave.

---

## Contrato de Integración Frontend ↔ Backend

El Frontend está alineado con el contrato v1 cerrado y funcional del Backend.

### 1. Carga del documento

- **Endpoint:** `POST {BASE_URL}/api/v1/documents`
- **Body:** `multipart/form-data` con campo `file`
- **Respuesta (201 Creado / 200 Duplicado existente):**
  ```json
  {
    "document_id": "doc_e7a935bc87ff",
    "filename": "documento.pdf",
    "status": "stored",
    "duplicate": false
  }
  ```
- Errores posibles: `400` (documento vacío), `413` (supera 10 MB), `415` (formato no soportado), `502` (fallo al almacenar).

### 2. Adaptación pedagógica del contenido

- **Endpoint:** `POST {BASE_URL}/api/v1/adaptations`
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "document_id": "doc_e7a935bc87ff",
    "target_profile": "beginner",
    "output_format": "flashcards",
    "niche_context": "backend"
  }
  ```

  | Campo | Valores permitidos |
  |---|---|
  | `target_profile` | `beginner` \| `intermediate` \| `advanced` |
  | `output_format` | `flashcards` \| `quiz` \| `tutorial` \| `summary` \| `all` |
  | `niche_context` | `general` \| `backend` \| `health` \| `legal` \| `business` \| `humanities` |

- **Response Body (200 OK):**
  ```json
  {
    "status": "completed",
    "document_id": "doc_e7a935bc87ff",
    "metadata": {
      "target_profile": "beginner",
      "output_format": "flashcards",
      "niche_context": "backend"
    },
    "quality_evaluation": {
      "source_faithfulness": 0.99,
      "pedagogical_coherence": 0.98,
      "overall_score": 0.985
    },
    "adapted_content": {
      "title": "Arquitectura Backend & Servidores",
      "flashcards": [
        {
          "front": "¿Qué es un Endpoint en una REST API?",
          "back": "Es una dirección URL específica para consultar o modificar datos en el servidor.",
          "didactic_hint": "Es como el buzón específico al que envías una solicitud."
        }
      ]
    }
  }
  ```

  El contenido de `adapted_content` varía según `output_format` solicitado:

  | `output_format` | Campo presente en `adapted_content` | Forma |
  |---|---|---|
  | `flashcards` | `flashcards` | Array de `{ front, back, didactic_hint }` |
  | `quiz` | `quiz` | `{ question, options[], correct_answer, explanation }` |
  | `tutorial` | `tutorial` | `{ title, duration, key_points[] }` |
  | `summary` | `summary` | `{ executive_summary, key_takeaways[], key_terms[] }` |
  | `all` | los cuatro campos anteriores juntos | — |

  `detail_level` está excluido del contrato v1: la profundidad y el tono se derivan directamente de `target_profile`.

### Manejo de errores

El cliente HTTP (`js/api/apiClient.js`) traduce las respuestas del Backend a mensajes legibles, desplegados mediante el diálogo de estado (`statusDialog.js`) y notificaciones toast (`notifications.js`). Códigos contemplados y probados: `200`, `201`, `400`, `404`, `408` (timeout de 30s), `413` (límite 10 MB), `415`, `422`, `500`, `502` (error OCI), y `0` (Backend no disponible / fallo de red).

---

## Estado Actual de la Integración (Sprint 2)

- **Carga y persistencia real en Backend y OCI (`POST /documents`):** ✅ **Funcional** (Tarea 1).
- **Límite máximo de 10 MB validado en cliente:** ✅ **Funcional** (Tarea 4).
- **Manejo UX integral de códigos HTTP y errores:** ✅ **Funcional** (Tarea 5).
- **Consulta y renderizado de la biblioteca (`GET /documents`):** ✅ **Funcional** (Tarea 6).
- **Consulta de formatos del libro (`GET /documents/{id}/formats`):** ✅ **Funcional** (Tarea 7).
- **Visualizador pedagógico de Quiz y Flashcards:** ✅ **Funcional** (Tarea 8).
- **Configuración desacoplada y Vite.js (sin URL hardcodeada):** ✅ **Funcional** (Tarea 3).
- **Modo único real (sin mocks):** ✅ **Completado**.

---

## 📌 Deuda Técnica Registrada (Integración Pipeline RAG / Agentes)

> **Registro Oficial de Deuda Técnica (Sprint 2):**  
> Actualmente la interfaz marca como completados los pasos posteriores a la subida en el stepper de carga (*Indexación/Embeddings*, *Vinculación de Formatos* y *Validación del Crítico*) mediante estados visuales temporales (`wait`), sin confirmación real en tiempo de ejecución por parte del Backend/Agentes (cuyo pipeline RAG opera de forma asíncrona).
>
> **Acción Futura Requerida (Sprint 3 / Próxima Iteración):**  
> Cuando el equipo de Backend y Agentes exponga el endpoint de seguimiento de procesos asíncronos (e.g. `GET /processes/{id}` o eventos en tiempo real SSE / WebSockets), estos pasos deberán sustituir la espera simulada por una escucha reactiva o sondeo del estado real del servicio (`PENDING` ➔ `PROCESSING` ➔ `COMPLETED` / `FAILED`), reflejando con fidelidad matemática el progreso del pipeline.
