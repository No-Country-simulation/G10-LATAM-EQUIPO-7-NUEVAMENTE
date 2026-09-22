# 🎓 NuevaMente - Frontend Modular (Flashcards & RAG Adaptativo)

Este módulo corresponde al **Frontend interactivo y modular** del proyecto **NuevaMente** (Hackathon ONE · Grupo 10). 
Desarrollado en **JavaScript moderno (ES6 Modules), HTML5 y CSS3** con arquitectura limpia (SRP), diseño Glassmorphism y animaciones 3D.

---

## 🚀 Cómo Ejecutar el Frontend Localmente

Debido a que usamos módulos nativos ES6 (`import / export`), los navegadores requieren que los archivos se sirvan a través de un servidor web local (para evitar restricciones de seguridad CORS en archivos `file://`).

Tienes cualquiera de estas 3 formas súper sencillas:

### Opción 1: Con Python (Recomendada)
Abre una terminal en la carpeta `frontend` y ejecuta:
```bash
python -m http.server 3000
```
Luego abre en tu navegador: [http://localhost:3000](http://localhost:3000)

### Opción 2: Con la extensión Live Server de VS Code
1. Abre la carpeta `frontend` en Visual Studio Code.
2. Haz clic derecho en `index.html`.
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
├── index.html                   # HTML semántico (orquestador de vistas SPA)
├── css/
│   ├── main.css                 # Importador central de hojas de estilo
│   ├── variables.css            # Tokens de diseño, Glassmorphism, temas claro/oscuro
│   ├── layout.css               # Header, navbar de pestañas principales y footer
│   ├── components.css           # Botones, badges, inputs, chips de conceptos
│   ├── bookshelf.css            # El Gran Librero 3D y Cuaderno Abierto en pantalla
│   ├── upload-tab.css           # Vista completa de Carga de Documento & Pipeline RAG
│   ├── notebook.css             # Cuaderno Interactivo Dinámico (portada, hojas, índice)
│   ├── study-hub.css            # Centro de Estudio (Flashcards 3D, Quiz, Video, Síntesis)
│   └── modals.css               # Modales de utilidad (Arquitectura RAG y Visor JSON)
├── js/
│   ├── config.js                # Configuración global, endpoints FastAPI y límites
│   ├── state.js                 # Almacén de estado reactivo global (Store con Observable)
│   ├── main.js                  # Punto de entrada y montaje de la aplicación
│   ├── api/
│   │   ├── apiClient.js         # Cliente HTTP fetch para FastAPI (multipart, health, RAG)
│   │   └── mockService.js       # Generador RAG adaptativo para cualquier materia (modo offline)
│   ├── data/
│   │   └── sampleLibrary.js     # Banco de 10 libros multidisciplinarios
│   └── modules/
│       ├── router.js            # Enrutador de pestañas (Librero, Cuaderno, Carga, Estudio)
│       ├── bookshelf.js         # Controlador del Librero 3D y Cuaderno Abierto
│       ├── uploadTab.js         # Controlador de la pestaña de carga y Stepper RAG
│       ├── notebook.js          # Renderizador del Cuaderno dinámico con animación 3D
│       ├── studyHub.js          # Orquestador del Centro de Estudio multi-formato
│       ├── flashcards.js        # Lógica de Flashcards 3D, volteo y atajos de teclado
│       ├── quiz.js              # Lógica de Quiz interactivo con justificación
│       ├── videoGuide.js        # Guion pedagógico y tutorial
│       ├── summary.js           # Síntesis ejecutiva RAG y términos clave
│       ├── jsonViewer.js        # Visor del JSON estructurado del Hackathon
│       └── theme.js             # Gestor de temas Claro / Oscuro
└── animacion3d.jpg / content.webp # Recursos visuales de transición y arquitectura
```

---

## 🧭 Experiencia de Usuario: Las 3 Pestañas Principales

1. 📚 **Pestaña 1: La Biblioteca de NuevaMente**
   - Estantería de madera noble con 10 tomos interactivos en CSS 3D correspondientes a diferentes disciplinas.
   - Al hacer clic en cualquier libro, este sale a pantalla como un **cuaderno abierto** con la ficha del documento y las 4 opciones de estudio inmediato.
   - Incluye el tomo especial `[ ➕ Subir Nuevo PDF ]` para incorporar nuevos documentos a la colección.

2. 📥 **Pestaña 2: Cargar Documento & Pipeline RAG (Pantalla Completa)**
   - Zona amplia de arrastrar y soltar (Drag & Drop) para PDF, DOCX, TXT o MD sobre fondo inmersivo de biblioteca.
   - Parámetros pedagógicos adaptativos: Perfil del estudiante (Principiante / Intermedio / Avanzado), Especialidad temática universal, Nivel de detalle y Formato.
   - Stepper visual en tiempo real de 4 etapas: **OCI Storage &rarr; ChromaDB &rarr; Agente Generador &rarr; Agente Revisor**.
   - Métricas de calidad y botón para ver el nuevo libro directamente en la biblioteca.

3. 📇 **Pestaña 3: Centro de Estudio Multi-Formato**
   - **Flashcards 3D**: Tarjetas con perspectiva 3D, pistas pedagógicas, contador de progreso y atajos de teclado (Espacio/Enter para voltear).
   - **Quiz Interactivo**: Preguntas de autoevaluación con validación inmediata, badges de acierto/error y justificación pedagógica.
   - **Tutorial / Video**: Estructura de guion pedagógico con marcas de tiempo.
   - **Resumen Ejecutivo**: Síntesis RAG con puntos clave y hashtags temáticos.
   - **Botón `{ } JSON`**: Inspección y copiado inmediato del JSON estructurado.

---

## 👥 Nota para el Equipo de Datos: Cómo Agregar o Reemplazar Muestras

Los ejemplos precargados se encuentran centralizados en:
👉 `frontend/js/data/sampleLibrary.js`

Para agregar nuevos datasets o retirar las muestras temporales, simplemente edita o sustituye los objetos exportados en ese archivo. Cada entrada define título, disciplina, metadatos y la lista de `sections` con sus flashcards, síntesis, video y quiz.
