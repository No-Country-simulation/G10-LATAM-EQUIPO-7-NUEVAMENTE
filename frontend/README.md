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

### 1. Carga del documento (POST /api/v1/documents)

- **Endpoint:** `POST {BASE_URL}/api/v1/documents`
- **Body:** `multipart/form-data` con campo `file` (PDF, TXT, MD; máx. 10 MB)
- **Respuesta (201 Creado / 200 Duplicado existente):**
  ```json
  {
    "document_id": "doc_e7a935bc87ff",
    "filename": "documento.pdf",
    "status": "stored",
    "duplicate": false
  }
  ```
- **Errores:** `400` (vacío), `413` (>10 MB), `415` (no soportado), `502` (fallo de persistencia OCI).

### 2. Adaptación pedagógica automática (POST /api/v1/adaptations)

- **Endpoint:** `POST {BASE_URL}/api/v1/adaptations`
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "document_id": "doc_e7a935bc87ff",
    "profile": "intermediate",
    "niche": "general",
    "detail_level": "detailed",
    "learning_objective": null
  }
  ```
- **Perfiles válidos:** `beginner`, `intermediate`, `advanced`.
- **Nichos temáticos:** `general`, `backend`, `health`, `legal`, `business`, `humanities`.
- **Nivel de detalle:** `detailed`, `standard`, `concise` (texto no vacío obligatorio).
- **Formatos automáticos:** En Sprint 2 el Backend indexa y genera automáticamente tanto `quiz` como `flashcards`. `output_format` ya no se envía.
- **Timeout en Frontend:** 120 segundos para permitir el tiempo de respuesta del LLM/RAG en modo síncrono.

### 3. Listar documentos para La Biblioteca (GET /api/v1/documents)

- **Endpoint:** `GET {BASE_URL}/api/v1/documents`
- **Content-Type:** `application/json`
- **Respuesta (200 OK):** Soporta tanto array directo `[...]` como wrapper `{ "items": [...] }`.
  ```json
  [
    {
      "document_id": "doc_123",
      "filename": "manual.pdf",
      "status": "stored",
      "size_bytes": 1048576,
      "created_at": "2026-09-30T12:00:00Z",
      "title": "Manual de Arquitectura",
      "summary": "Resumen ejecutivo del documento analizado."
    }
  ]
  ```

### 4. Consultar detalle del documento (GET /api/v1/documents/{document_id})

- **Endpoint:** `GET {BASE_URL}/api/v1/documents/{document_id}`
- **Respuesta (200 OK):**
  ```json
  {
    "document_id": "doc_123",
    "filename": "manual.pdf",
    "status": "indexed",
    "content_type": "application/pdf",
    "size_bytes": 1048576,
    "created_at": "2026-09-30T12:00:00Z",
    "updated_at": "2026-09-30T12:05:00Z",
    "title": "Manual de Arquitectura",
    "summary": "Resumen ejecutivo del documento analizado.",
    "estimated_time": "10 min"
  }
  ```

### 5. Consultar formatos generados (GET /api/v1/documents/{document_id}/formats)

- **Endpoint:** `GET {BASE_URL}/api/v1/documents/{document_id}/formats`
- **Respuesta (200 OK):** Contrato canónico acordado entre Backend, Agentes, Data/IA y Frontend.
  ```json
  {
    "document_id": "doc_123",
    "status": "ready",
    "formats": {
      "quiz": {
        "format_id": "fmt_quiz_123",
        "status": "success",
        "content": {
          "title": "Quiz de arquitectura de software",
          "instructions": "Seleccione la respuesta correcta.",
          "questions": [
            {
              "question_id": "q1",
              "question": "¿Qué caracteriza a un microservicio?",
              "options": [
                "Despliegue independiente",
                "Base de datos obligatoriamente compartida",
                "Una única aplicación monolítica",
                "Ausencia de interfaces"
              ],
              "correct_answer": "Despliegue independiente",
              "explanation": "Un microservicio puede desplegarse y evolucionar de manera independiente."
            }
          ]
        },
        "error_message": null
      },
      "flashcards": {
        "format_id": "fmt_flashcards_123",
        "status": "success",
        "content": {
          "title": "Flashcards de arquitectura de software",
          "instructions": "Revise cada concepto y su explicación.",
          "cards": [
            {
              "card_id": "card_1",
              "front": "Microservicio",
              "back": "Servicio pequeño que puede desplegarse y evolucionar independientemente."
            }
          ]
        },
        "error_message": null
      }
    }
  }
  ```

  - **Estados por formato:** `success`, `failed`, `no_results`.
  - **Estados globales del endpoint:**
    - `pending`: documento almacenado, adaptación aún no iniciada.
    - `processing`: indexación o generación en curso.
    - `ready`: Quiz y Flashcards disponibles.
    - `partial`: al menos un formato exitoso.
    - `error`: procesamiento o generación fallida.
  - **Resolución didáctica:** En Frontend, `quiz.js` resuelve `correct_answer` tanto por texto exacto de la opción como por índice numérico; `flashcards.js` renderiza `content.cards` y mensajes pedagógicos ante fallos parciales o estados en proceso (`processing`).

### Manejo de errores

El cliente HTTP (`js/api/apiClient.js`) traduce las respuestas del Backend a mensajes legibles, desplegados mediante el diálogo de estado (`statusDialog.js`) y notificaciones toast (`notifications.js`). Códigos contemplados y probados: `200`, `201`, `400`, `404`, `408` (timeout de 30s/120s), `413` (límite 10 MB), `415`, `422`, `500`, `502` (error OCI), y `0` (Backend no disponible / fallo de red).

---

## Estado Actual de la Integración (Sprint 2)

- **Carga y persistencia real en Backend y OCI (`POST /documents`):** ✅ **Funcional** (Tarea 1).
- **Flujo real de adaptación pedagógica (`POST /adaptations`):** ✅ **Funcional** (Flujo RAG + IA cerrado sin esperas simuladas).
- **Límite máximo de 10 MB validado en cliente:** ✅ **Funcional** (Tarea 4).
- **Manejo UX integral de códigos HTTP y errores:** ✅ **Funcional** (Tarea 5).
- **Consulta y renderizado de la biblioteca (`GET /documents`):** ✅ **Funcional** (Tarea 6).
- **Consulta de formatos del libro (`GET /documents/{id}/formats`):** ✅ **Funcional** (Tarea 7).
- **Visualizador pedagógico de Quiz y Flashcards:** ✅ **Funcional** (Tarea 8).
- **Configuración desacoplada y Vite.js (sin URL hardcodeada):** ✅ **Funcional** (Tarea 3).
- **Modo único real (sin mocks):** ✅ **Completado**.
