# 🎓 NuevaMente - Frontend Modular (Flashcards, Librero 3D & RAG Adaptativo)

Este módulo corresponde al **Frontend interactivo y modular** de la plataforma **NuevaMente** (Hackathon ONE · Grupo 10 · LATAM).  
Desarrollado en **JavaScript moderno (ES6 Modules), HTML5 y CSS3** bajo principios de arquitectura limpia y Responsabilidad Única (SRP), con diseño Glassmorphism, animaciones 3D e identidad visual cinematográfica.

---

## 🚀 Cómo Ejecutar el Frontend Localmente

Debido al uso de módulos nativos ES6 (`import / export`), los navegadores requieren que los archivos se sirvan a través de un servidor web local (para evitar restricciones de seguridad CORS en archivos locales `file://`).

Tienes cualquiera de estas 3 formas sencillas:

### Opción 1: Con Python (Recomendada)
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

---

## 📁 Arquitectura Modular de Carpetas

El frontend se encuentra estructurado en capas desacopladas con Responsabilidad Única (SRP):

```
frontend/
├── index.html                   # Orquestador de vistas SPA (Single Page Application)
├── LogoPropuesta - Editado.png   # Logo e identidad oficial activa de NuevaMente
├── biblioteca.jpg               # Fondo sereno y luminoso de la biblioteca clásica
├── portada.jpg                  # Fondo cinematográfico de la portada de bienvenida
├── content.webp                 # Diagrama funcional de Arquitectura RAG & Multiagente
├── README.md                    # Documentación del módulo frontend
├── css/
│   ├── main.css                 # Importador central de hojas de estilo modulares
│   ├── variables.css            # Tokens de diseño, Glassmorphism, paleta dorada/cyan y temas
│   ├── layout.css               # Header, navbar de pestañas principales y status bar
│   ├── components.css           # Botones, badges, inputs y chips de conceptos
│   ├── bookshelf.css            # El Gran Librero 3D y Cuaderno Abierto realista
│   ├── upload-tab.css           # Vista completa de Carga de Documento & Pipeline RAG
│   ├── notebook.css             # Cuaderno Interactivo Dinámico (hojas, índice y lectura)
│   ├── study-hub.css            # Centro de Estudio (Flashcards 3D, Quiz, Video, Síntesis)
│   ├── portada.css              # Portada de bienvenida inmersiva a pantalla completa
│   └── modals.css               # Modales de utilidad (Arquitectura RAG y Visor JSON)
└── js/
    ├── config.js                # Configuración global, endpoints FastAPI y límites
    ├── state.js                 # Almacén de estado reactivo global (Store con Observable)
    ├── main.js                  # Punto de entrada y montaje de la aplicación
    ├── api/
    │   ├── apiClient.js         # Cliente HTTP fetch para FastAPI (multipart, health, RAG)
    │   └── mockService.js       # Generador RAG adaptativo para cualquier materia (modo offline)
    │
    ├── data/
    │   └── sampleLibrary.js     # Banco de 10 tomos multidisciplinarios precargados
    │
    └── modules/
        ├── router.js            # Enrutador de pestañas (Librero, Carga, Centro de Estudio)
        ├── portada.js           # Controlador de la portada de bienvenida y transición
        ├── bookshelf.js         # Controlador del Librero 3D y Cuaderno Abierto
        ├── uploadTab.js         # Controlador de la pestaña de carga y Stepper RAG
        ├── notebook.js          # Renderizador del Cuaderno dinámico con animación 3D
        ├── studyHub.js          # Orquestador del Centro de Estudio multi-formato
        ├── flashcards.js        # Lógica de Flashcards 3D, volteo y atajos de teclado
        ├── quiz.js              # Lógica de Quiz interactivo con justificación pedagógica
        ├── videoGuide.js        # Guion didáctico y tutorial adaptativo
        ├── summary.js           # Síntesis ejecutiva RAG y términos clave
        ├── jsonViewer.js        # Visor del JSON estructurado del Hackathon
        └── theme.js             # Gestor de temas Claro / Oscuro
```

---

## 🧭 Flujo y Experiencia de Usuario

1. 🏛️ **Portada de Bienvenida (Splash Cover Inmersivo)**
   - Vista cinematográfica de pantalla completa con el logo oficial y badge del Hackathon ONE.
   - Haz clic en cualquier lugar o en el botón dorado para una transición fluida al interior de la biblioteca.
   - Puedes regresar a la portada en cualquier momento haciendo clic en el logo de la barra superior.

2. 📚 **La Biblioteca de NuevaMente (Pilar 1)**
   - Estantería de madera noble con 10 tomos interactivos en CSS 3D correspondientes a diversas disciplinas científicas y humanísticas.
   - Al hacer clic en cualquier libro, este se despliega en un **cuaderno abierto realista** con el detalle del documento, métricas RAG y las 4 opciones de estudio inmediato.
   - Incluye el tomo especial `[ ➕ Subir Nuevo PDF ]` para saltar directamente al pipeline de ingesta.

3. 📥 **Cargar & Pipeline RAG Adaptativo (Pilar 2)**
   - Zona amplia de arrastrar y soltar (Drag & Drop) para PDF, DOCX, TXT o MD.
   - Selector de parámetros pedagógicos adaptativos: Perfil del estudiante (Principiante / Intermedio / Avanzado), Especialidad temática universal, Nivel de detalle y Formato de salida.
   - Stepper visual de 4 etapas: **OCI Storage &rarr; ChromaDB &rarr; Agente Generador &rarr; Agente Revisor**.
   - Conexión dual mediante selector en el header: **Modo Mock autónomo** (offline) o **Modo Backend Real** (FastAPI).

4. 📇 **Centro de Estudio Multi-Formato (Pilar 3)**
   - **Flashcards 3D**: Tarjetas con perspectiva y animación de volteo realista, pistas pedagógicas, contador de progreso y atajos de teclado (Espacio/Enter para voltear).
   - **Quiz Interactivo**: Preguntas de autoevaluación con validación inmediata, badges de acierto/error y justificación pedagógica.
   - **Tutorial / Video**: Estructura de guion pedagógico con marcas de tiempo y bloques temáticos.
   - **Resumen Ejecutivo**: Síntesis RAG con puntos clave, conceptos esenciales y hashtags temáticos.
   - **Botón `{ } JSON`**: Inspección y copiado inmediato de la respuesta estructurada según el schema del Hackathon.

---

## 👥 Nota para el Equipo de Datos / Backend: Cómo Personalizar las Muestras

Los ejemplos precargados se encuentran centralizados en:
👉 `frontend/js/data/sampleLibrary.js`

Para agregar nuevos datasets o retirar las muestras temporales, simplemente edita o sustituye los objetos exportados en ese archivo. Cada entrada define título, disciplina, metadatos y la lista de `sections` con sus flashcards, síntesis, tutorial y quiz.
