# NuevaMente - Frontend

Este módulo corresponde al **Frontend** de la plataforma **NuevaMente** (Hackathon ONE · Grupo 10 · LATAM).
Está desarrollado con **JavaScript moderno (ES Modules), HTML5 y CSS3**, sin framework de UI. Vite sirve la aplicación durante el desarrollo y genera el bundle de producción; Docker publica ese bundle con Nginx. La interfaz usa una navegación SPA por pestañas, diseño Glassmorphism y tema oscuro.

---

## Cómo Ejecutar el Frontend Localmente

Debido al uso de módulos ES (`import` / `export`), la aplicación debe servirse por HTTP; no se debe abrir `index.html` directamente con `file://`.

La opción recomendada es Vite. Desde `frontend/`:

```bash
npm install
npm run dev
```

El servidor escucha en [http://localhost:3000](http://localhost:3000) y abre el navegador automáticamente. Para crear y previsualizar el bundle de producción:

```bash
npm run build
npm run preview
```

También se puede servir el HTML estático durante desarrollo, pero esa opción no carga las variables `.env` de Vite:

```bash
python -m http.server 3000
```

### Conexión con Backend (FastAPI)

La URL base se resuelve en este orden: `VITE_API_BASE_URL` de Vite, `window.__ENV__.VITE_API_BASE_URL`, los parámetros `?api=` o `?backend=`, el valor guardado en `localStorage` (`nuevamente_backend_url`), el mismo origen cuando el host no es `localhost`/`127.0.0.1`, y finalmente `http://localhost:8000`.

Para desarrollo local, copia `.env.example` a `.env` y ajusta `VITE_API_BASE_URL` si el Backend no está en `http://localhost:8000`. `VITE_API_TIMEOUT_MS` configura el timeout HTTP estándar (30 s por defecto); la carga usa un límite independiente de 120 s. En Docker, ambas variables se reciben como argumentos de build. El badge del encabezado refleja el chequeo de `GET /api/v1/health`, realizado al iniciar y cada 60 segundos.

---

## Arquitectura Modular de Carpetas

```
frontend/
├── index.html                   # Orquestador de vistas SPA (Single Page Application)
├── README.md                    # Este documento
├── package.json                 # Scripts dev/build/preview y dependencia de Vite
├── package-lock.json            # Versiones bloqueadas para instalación reproducible
├── vite.config.js               # Servidor de desarrollo y salida dist/
├── Dockerfile                   # Build Vite y publicación con Nginx
├── nginx.conf                   # Servido SPA y proxy hacia Backend
├── .env.example                 # Variables públicas de configuración del Front
├── css/
│   ├── main.css                 # Importador central de hojas de estilo modulares
│   ├── variables.css            # Tokens de diseño, Glassmorphism y paleta dorada/cyan
│   ├── layout.css               # Header, navbar de pestañas principales y barra de estado
│   ├── components.css           # Botones, badges, inputs, chips y notificaciones toast
│   ├── bookshelf.css            # Catálogo de libros y modal de documento
│   ├── upload-tab.css           # Vista de Carga de Documento, stepper y panel de pruebas
│   ├── notebook.css             # Cuaderno Interactivo Dinámico (hojas, índice y lectura)
│   ├── study-hub.css            # Centro de Estudio y estilos de auditoría de evaluación
│   ├── portada.css              # Portada de bienvenida a pantalla completa
│   └── modals.css               # Modales de utilidad y diálogo de estado del Backend
└── js/
    ├── config.js                # Configuración de API, límites y valores por defecto
    ├── state.js                 # Estado global observable y preferencias locales
    ├── main.js                  # Punto de entrada y montaje de la aplicación
    ├── api/
    │   └── apiClient.js         # Cliente HTTP fetch hacia el Backend (FastAPI real)
    └── modules/
        ├── router.js            # Navegación de pestañas (Biblioteca, Carga, Centro de Estudio)
        ├── portada.js           # Controlador de la portada de bienvenida y transición
        ├── bookshelf.js         # Controlador del Librero 3D y el Cuaderno Abierto
        ├── uploadTab.js         # Controlador de carga, parámetros y flujo real con el Backend
        ├── notifications.js     # Sistema de notificaciones toast (éxito, error, advertencia)
        ├── statusDialog.js      # Diálogo de estado tras cada respuesta del Backend
        ├── notebook.js          # Renderizador del Cuaderno dinámico
        ├── studyHub.js          # Orquestador del Centro de Estudio multi-formato
        ├── flashcards.js        # Lógica de Flashcards, volteo y atajos de teclado
        ├── quiz.js              # Lógica de Quiz interactivo con justificación pedagógica
        ├── videoGuide.js        # Guion audiovisual por escenas
        ├── summary.js           # Síntesis ejecutiva y términos clave
        ├── evaluatorMetrics.js  # Auditoría de evaluaciones V1/V2 y ciclos
        └── utils/
            └── friendlyError.js # Normalización de errores para la interfaz
```

---

## Flujo y Experiencia de Usuario

1. **Portada de Bienvenida**
   Vista de pantalla completa con el logo del proyecto. Un clic transiciona a la biblioteca.

2. **La Biblioteca**
   Estantería de libros interactivos en 3D. Al hacer clic en cualquiera, se despliega un cuaderno abierto con el detalle del documento (tiempo de lectura, cantidad de secciones, nivel) y las opciones de estudio disponibles.

3. **Carga de Documento**
   Zona de arrastrar y soltar para PDF, Markdown o TXT (hasta 10 MB). Permite seleccionar perfil, área temática, nivel de detalle y objetivo de aprendizaje opcional. El Front sube el archivo y esos parámetros al Backend; la indexación se completa antes de responder y la generación de Quiz, Flashcards, TLDR y Video Script se inicia en segundo plano. La interfaz consulta los estados de los formatos y permite ir al Catálogo o al Centro de Estudio.

4. **Centro de Estudio**
   - **Flashcards**: tarjetas con animación de volteo y pistas pedagógicas.
   - **Quiz**: preguntas de autoevaluación con validación inmediata y justificación.
   - **Guion de video**: escenas con narración, descripción visual y duración.
   - **Resumen**: síntesis ejecutiva con puntos clave y términos clave.

---

## Integración con Backend

El cliente HTTP está en `js/api/apiClient.js`; las rutas se construyen con el prefijo `/api/v1`. En la carga, el navegador crea el `multipart/form-data` y no se fuerza manualmente el header `Content-Type`.

| Método y endpoint | Uso en Frontend |
|---|---|
| `GET /api/v1/health` | Comprueba la conexión al iniciar y cada 60 segundos. |
| `POST /api/v1/documents` | Envía el archivo y el contexto pedagógico; devuelve `201` para nuevo y `200` para duplicado. |
| `GET /api/v1/documents` | Carga el catálogo; el contrato actual del Backend devuelve `{ "documents": [...] }`. |
| `GET /api/v1/documents/{id}` | Consulta metadata y completa los datos pedagógicos visibles si están disponibles. |
| `GET /api/v1/documents/{id}/formats` | Recupera el estado y los cuatro formatos generados, con su contenido y evaluaciones del ciclo. |
| `POST /api/v1/documents/{id}/formats/regenerate` | Inicia la regeneración asíncrona de uno o varios formatos. |
| `GET /api/v1/documents/{id}/download` | Descarga el archivo original. |
| `PATCH /api/v1/documents/{id}/deactivate` | Inactiva lógicamente un documento del Catálogo (`204 No Content`). |

### Carga de documentos

`POST /api/v1/documents` recibe `multipart/form-data`:

- `file` (obligatorio): archivo PDF, Markdown (`.md`) o TXT, máximo 10 MiB.
- `profile` (obligatorio): `beginner`, `intermediate` o `advanced`.
- `niche` (obligatorio): `general`, `backend`, `health`, `legal`, `business` o `humanities`.
- `detail_level` (obligatorio): texto no vacío.
- `learning_objective` (opcional): texto no vacío si se envía.

El Front valida extensión, tamaño y archivo vacío antes del envío. No envía `document_id`, formatos ni chunks: el Backend almacena e indexa el documento y programa la generación asíncrona de `quiz`, `flashcards`, `tldr` y `video_script`. La respuesta de carga contiene `document_id`, `filename`, `status` y `duplicate`; los formatos se consultan por separado.

### Consulta de formatos y evaluación

`GET /api/v1/documents/{id}/formats` devuelve el estado agregado (`pending`, `processing`, `ready`, `partial` o `error`) y, cuando existen, objetos para `quiz`, `flashcards`, `tldr` y `video_script`. Cada objeto incluye `format_id`, `status` (`processing`, `success`, `failed` o `no_results`), `content`, `error_message`, `evaluation` y `evaluations`. La estructura de `content` varía por formato: preguntas, tarjetas, resumen o escenas.

El Front consulta mientras el estado agregado sea `pending` o `processing`, y renderiza fallos parciales por formato. La evaluación presentada en el modal de auditoría proviene del Backend: veredicto, scores heurísticos y semánticos separados, observaciones, recomendaciones, información no respaldada y metadatos técnicos. Cada evaluación puede incluir `evaluator_version` y `rubric_version`; `semantic_evaluation` incluye además `prompt_version`, `model` y `latency_ms`. El modal muestra las versiones del evaluator y de la rúbrica, el modelo y la latencia; recibe también la versión del prompt en el objeto semántico, aunque no la presenta actualmente. Si hay varias evaluaciones en el ciclo, permite navegar entre ellas. El Front no evalúa el contenido ni calcula un score combinado.

La regeneración envía `POST /api/v1/documents/{id}/formats/regenerate` con `{ "formats": ["quiz"] }` (uno o más formatos ya intentados). El Backend devuelve `202 Accepted` y nuevos `format_id`; el Front inicia el polling de esos intentos. La generación y evaluación se ejecutan en Backend/Data/IA.

### Manejo de errores

El cliente HTTP convierte los errores HTTP y de red en `ApiError`; `friendlyError.js`, el diálogo de estado y las notificaciones los presentan en la interfaz. El cliente maneja, entre otros, `400`, `404`, `408`, `409`, `413`, `415`, `422`, `500` y `502`; el estado `0` representa fallo de conexión. La carga tiene un timeout de 120 s y las solicitudes generales usan el timeout configurado (30 s por defecto).

## Límites y pendientes técnicos identificados

Esta sección recoge límites observables en el código actual; no representa un backlog priorizado:

- `package.json` define `dev`, `build` y `preview`, pero no tiene script de pruebas automatizadas para el Frontend.
- El Front depende de Backend para persistir documentos, generar/revisar formatos, exponer evaluaciones y mantener el historial; no implementa esos servicios en el navegador.
- La documentación y los cambios de integración deben mantenerse sincronizados con los contratos activos de Backend, en particular los estados agregados y los campos de `evaluation`/`evaluations`.
