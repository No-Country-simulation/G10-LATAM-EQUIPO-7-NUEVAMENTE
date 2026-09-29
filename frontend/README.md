# NuevaMente - Frontend

Este módulo corresponde al **Frontend** de la plataforma **NuevaMente** (Hackathon ONE · Grupo 10 · LATAM).
Desarrollado en **JavaScript moderno (ES6 Modules), HTML5 y CSS3**, sin frameworks ni paso de build, bajo principios de arquitectura limpia y Responsabilidad Única (SRP), con diseño Glassmorphism y modo oscuro fijo.

---

## Cómo Ejecutar el Frontend Localmente

Debido al uso de módulos nativos ES6 (`import` / `export`), los navegadores requieren que los archivos se sirvan a través de un servidor web local (no funciona abriendo `index.html` directo con `file://`, por restricciones de CORS del navegador).

Tienes cualquiera de estas 3 formas sencillas:

### Opción 1: Con Python
Abre tu terminal en la carpeta `frontend` y ejecuta:
```bash
python -m http.server 3000
```
Luego abre en tu navegador: [http://localhost:3000](http://localhost:3000)

### Opción 2: Con la extensión Live Server de VS Code
1. Abre la carpeta `frontend` en Visual Studio Code.
2. Haz clic derecho sobre `index.html`.
3. Selecciona **"Open with Live Server"**.

### Opción 3: Con Node / npx
```bash
npx serve .
```

### Backend en paralelo

El Frontend está conectado exclusivamente al Backend real (FastAPI) — ya no existe un modo demo/mock alternable desde la interfaz. Para que la carga y generación de contenido funcionen, el Backend debe estar corriendo en simultáneo (por defecto en `http://localhost:8000`, ver [`../backend/README.md`](../backend/README.md)), con CORS habilitado para el origen donde sirvas el Frontend.

> **Limitación conocida:** la URL del Backend está definida como constante en `js/config.js` (`CONFIG.API.DEFAULT_BASE_URL`). Si corrés el Backend en otro host/puerto, hay que editar ese archivo a mano. Reemplazar esto por variables de entorno (por ejemplo mediante Vite) es una tarea pendiente del Sprint 2, todavía no implementada.

---

## Arquitectura Modular de Carpetas

```
frontend/
├── index.html                   # Orquestador de vistas SPA (Single Page Application)
├── README.md                    # Este documento
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
    ├── config.js                # Configuración global, endpoints del Backend y límites
    ├── state.js                 # Almacén de estado reactivo global (Store con Observable)
    ├── main.js                  # Punto de entrada y montaje de la aplicación
    ├── api/
    │   ├── apiClient.js         # Cliente HTTP fetch hacia el Backend (multipart, adaptación)
    │   └── mockService.js       # Utilidades compartidas de generación (inferencia de disciplina)
    │
    ├── data/
    │   └── sampleLibrary.js     # Banco de documentos de muestra precargados
    │
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

Ambos endpoints devuelven errores en un formato consistente que el Frontend traduce a mensajes legibles (`js/api/apiClient.js`), y que se muestran al usuario mediante el diálogo de estado (`statusDialog.js`) y notificaciones toast (`notifications.js`). Códigos contemplados: `400`, `404`, `408` (timeout), `413`, `415`, `422`, `500`, `502`, y `0` (Backend no disponible / CORS).

---

## Estado actual de la integración

- Carga y persistencia real de documentos contra el Backend: **funcional**.
- Solicitud de adaptación pedagógica (`/adaptations`) contra el Backend: **funcional**, usando el contrato descrito arriba.
- Manejo de errores end-to-end (archivo inválido, backend caído, timeout, duplicados): **implementado**.
- Configuración de la URL del Backend por entorno (sin hardcodear): **pendiente**.
