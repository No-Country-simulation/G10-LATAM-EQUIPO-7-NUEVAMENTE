# 📋 Reglas del Proyecto — NuevaMente (Sprint 2)

Este documento define las directrices arquitectónicas, técnicas y de comportamiento para el asistente de IA en el repositorio **NuevaMente** durante el **Sprint 2**.

---

## 👤 1. Perfil del Usuario y Ámbito del Agente

- **Rol del Usuario:** Desarrollador **Frontend** exclusivamente.
- **Enfoque del Asistente:** Actuar como **Senior Frontend Pair Programmer** y asesor de integración cliente-servidor.
- **Restricción de Alcance (No Intrusión):**
  - Todas las modificaciones de código, refactorizaciones y creaciones de archivos deben limitarse al directorio `frontend/`.
  - **No modificar** código de `backend/`, `agentes/` (RAG) ni `Data_IA/`, salvo que el usuario lo solicite explícitamente para validar contratos o pruebas de integración local.
  - Al brindar explicaciones o resolver dudas de arquitectura general, siempre enfocar la solución desde la perspectiva del cliente (Frontend).

---

## 🏛️ 2. Arquitectura y Stack de Frontend

El frontend mantiene una arquitectura modular y desacoplada con Responsabilidad Única (SRP):

1. **Stack Tecnológico:**
   - **JavaScript Moderno (ES6 Modules):** Modularización nativa mediante `import` y `export`, sin frameworks pesados (React, Vue, etc.) a menos que se acuerde una migración explícita.
   - **HTML5 Semántico:** Vistas y componentes organizados bajo Single Page Application (SPA).
   - **CSS3 Puro:** Diseño Glassmorphism, animaciones 3D, tokens centralizados y variables nativas.

2. **Estructura y Responsabilidad Única (SRP):**
   - `frontend/css/`:
     - `variables.css`: Tokens de diseño, paleta (oro/cian/glassmorphism), tipografías y temas.
     - `layout.css`, `components.css`: Estilos estructurales y componentes reutilizables (botones, chips, modales).
     - Hojas por vista: `bookshelf.css`, `notebook.css`, `study-hub.css`, `upload-tab.css`, `portada.css`, `modals.css`.
   - `frontend/js/`:
     - `config.js`: Centralización de URLs del Backend, endpoints y límites.
     - `state.js`: Store centralizado reactivo (Observable) para sincronizar el estado global.
     - `api/apiClient.js`: Cliente HTTP centralizado (`fetch`) para Backend real con manejo unificado de headers y errores.
     - `modules/`: Controladores desacoplados por vista (`router.js`, `bookshelf.js`, `uploadTab.js`, `notebook.js`, `studyHub.js`, `flashcards.js`, `quiz.js`, `theme.js`).

3. **Modo Único: Conexión Exclusiva con Backend Real:**
   - **Se descarta el Modo Mock / Modo Dual.** La aplicación se conecta de forma directa y exclusiva con la API de Backend (FastAPI).
   - No mantener lógica bifurcada de mocks si ya no es necesaria; todo el flujo se apoya en los endpoints reales del backend.

---

## 🚀 3. Directrices y Contratos del Sprint 2

Basadas en el planning oficial y los diagramas de arquitectura:

### 3.1 Frontera Arquitectónica Inviolable
- **Frontend se comunica ÚNICAMENTE con Backend API:**
  - Frontend **NUNCA** consulta directamente a Oracle Cloud Infrastructure (OCI Object Storage).
  - Frontend **NUNCA** accede a la Base de Datos de negocio.
  - Frontend **NUNCA** se conecta directamente con el pipeline de Agentes/RAG.
- Toda operación de subida, consulta de catálogo, detalle o formatos pasa exclusivamente por Backend.

### 3.2 Alcance Funcional de Formatos en Sprint 2
- El sprint se enfoca activamente en dos formatos:
  1. **Quiz**
  2. **Flashcards**
- **Arquitectura Extensible:** Mantener la capacidad interna en la UI para soportar formatos futuros (Tutoriales, Resúmenes) sin romper la experiencia actual ni generar errores.

### 3.3 Flujo de Consulta desde la Biblioteca (Diagrama C)
1. **Biblioteca:**
   - Frontend realiza `GET /documents` al abrir la biblioteca.
   - Backend devuelve la lista de documentos persistidos: `id`, `título`, `nombre corto`, `estado`, `resumen breve`.
   - Frontend dibuja la lista/estantería de libros existentes.
2. **Detalle de Documento:**
   - Al abrir un libro, Frontend realiza `GET /documents/{id}`.
   - Backend retorna la metadata: `título`, `resumen`, `tiempo estimado`, `estado`.
   - Frontend renderiza el cuaderno/detalle del documento.
3. **Formatos Generados:**
   - Frontend realiza `GET /documents/{id}/formats`.
   - Backend retorna los formatos persistidos (`quiz`, `flashcards`).
   - Frontend visualiza el Quiz y las Flashcards correspondientes.
*(Nota: Este flujo solo consulta información ya persistida, no dispara indexación ni participa Agentes directamente).*

### 3.4 Flujo de Ingesta y Resiliencia
- **Subida:** `POST /documents` (multipart/form-data con archivo). Backend orquesta OCI, BD, indexación y generación automática de Quiz + Flashcards.
- **Manejo de Estados Parciales:** Si un formato falla (ej. Quiz listo, Flashcards fallido), renderizar el exitoso e indicar el error amigablemente con opción de reintento. Manejar estados: `UPLOADED`, `PROCESSING`, `PARTIAL`, `READY`, `ERROR`.
- **Validaciones:** Límite máximo de **10 MB** por archivo y extensiones permitidas (PDF, DOCX, TXT, MD).

---

## 📋 4. Backlog de Tareas de Frontend (Trello Sprint 2)

Las 8 tareas oficiales del tablero de Frontend a desarrollar una por una:

1. 🔲 **Tarea 1:** Ajustar el flujo real para cuando `POST /documents` termine correctamente.
2. 🔲 **Tarea 2:** Corregir la documentación/adaptations y su contrato ya cerrados y funcionales.
3. 🔲 **Tarea 3:** URL del Backend hardcodeada - Validar implementación de Vite.js / configuración desacoplada.
4. ✅ **Tarea 4:** Tamaño máximo de 10 MB en Frontend. *(Completado y probado)*
5. ✅ **Tarea 5:** Manejo UX de errores. *(Completado y probado: 200, 201, 400, 404, 413, 415, 422, 502, 500, timeout y red)*
6. 🔲 **Tarea 6:** Solicitar y dibujar los libros existentes (`GET /documents`).
7. 🔲 **Tarea 7:** Solicitar los formatos al Backend del libro abierto (`GET /documents/{id}/formats`).
8. 🔲 **Tarea 8:** Presentar la información (`Quiz` - `Flashcards`).

---

## 🎯 5. Política de Trabajo por Tareas y Entregas a QA

Para no sobrecargar al equipo de QA y asegurar la estabilidad de la rama:

1. **Una Tarea a la Vez (Desarrollo Atómico):**
   - Abordar cada funcionalidad o corrección como una unidad de trabajo independiente y bien delimitada.
2. **Push Probado y 100% Funcional:**
   - **Queda prohibido realizar push o abrir PR con código a medio terminar o con errores rotos.**
   - Cada tarea terminada debe estar **probada localmente** y funcionando antes de hacer commit/push.
3. **Flujo de Verificación Previo al Push:**
   - Probar en navegador sirviendo desde `frontend/`:
     - Con Python: `python -m http.server 3000`
     - Con Live Server o `npx serve .`
   - Validar en consola del navegador (F12) que no existan errores de JavaScript ni llamadas rotas.
   - Revisar el `git diff` para asegurar que solo se toquen los archivos correspondientes a la tarea.
4. **Ramas y Flujo Git:**
   - Trabajar en la rama correspondiente de frontend o feature.
   - Integrar hacia `QA` únicamente entregas limpias, probadas y acompañadas de una descripción clara de lo implementado.
