# NuevaMente — Frontend

Aplicación web de NuevaMente construida con HTML, CSS y JavaScript ES modules.
Vite proporciona el servidor de desarrollo y empaqueta los archivos estáticos
para producción. La interfaz es una SPA ligera, sin framework de UI, y utiliza
BackendAPI como única API de negocio.

Para conocer el flujo global del producto, consulta el [README de la raíz](../README.md).
Los contratos y la operación del servidor están en el [README de BackendAPI](../backend/README.md).

## Navegación

| Si buscas… | Consulta… |
|---|---|
| Pantallas y capacidades visibles | [Experiencia de usuario](#experiencia-de-usuario) |
| Módulos y responsabilidades de código | [Arquitectura del frontend](#arquitectura-del-frontend) |
| Endpoints consumidos y ciclo de formatos | [Integración con BackendAPI](#integración-con-backendapi) |
| Configurar la dirección de BackendAPI | [Configuración](#configuración) |
| Ejecutar en desarrollo o producción | [Desarrollo y despliegue](#desarrollo-y-despliegue) |

## Experiencia de usuario

La interfaz se organiza en tres vistas principales, más una portada de bienvenida:

1. **Catálogo de capacitaciones:** consulta los documentos persistidos en
   BackendAPI, permite buscarlos/filtrarlos, alterna entre vista de lista y
   estantería interactiva, y muestra el detalle del documento.
2. **Carga de documento:** acepta PDF, Markdown (`.md`) y TXT de hasta 10 MiB.
   Permite elegir perfil, nicho y nivel de detalle antes de cargar.
3. **Centro de capacitación:** presenta los cuatro formatos soportados por el
   producto: Quiz (`quiz`), Flashcards (`flashcards`), Resumen (`tldr`) y Guion
   formativo (`video_script`). También permite regenerar formatos y descargar
   el archivo original.

El contenido de los documentos, sus estados y los resultados educativos se
obtienen de BackendAPI. El frontend no implementa una generación local ni un
modo de datos mock.

## Arquitectura del frontend

```text
index.html
  ├── js/main.js                 Bootstrap e inicialización
  ├── js/state.js                Estado observable compartido
  ├── js/config.js               Configuración y endpoints
  ├── js/api/apiClient.js        Cliente HTTP y normalización de errores
  └── js/modules/
      ├── router.js              Vistas principales
      ├── portada.js             Portada de bienvenida
      ├── bookshelf.js            Catálogo, búsqueda y detalle de documentos
      ├── uploadTab.js            Selección, validación y carga de archivos
      ├── studyHub.js             Estados, polling y regeneración
      ├── flashcards.js           Vista de tarjetas
      ├── quiz.js                 Vista de Quiz
      ├── summary.js              Vista de resumen
      ├── videoGuide.js           Vista de guion formativo
      ├── statusDialog.js         Diálogo de estados y errores
      ├── notifications.js        Notificaciones toast
      └── utils/friendlyError.js  Mensajes de error para la interfaz
```

Los estilos están en `css/`; `css/main.css` reúne las hojas modulares. El estado
observable conserva, entre otros datos, la vista activa, el documento
seleccionado, los parámetros de adaptación, la conexión con BackendAPI y los
formatos del documento actual.

## Integración con BackendAPI

El cliente `js/api/apiClient.js` consume estos endpoints bajo el prefijo
`/api/v1`:

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/health` | Verificación de conectividad al iniciar y cada 60 segundos. |
| `GET` | `/documents` | Cargar documentos del catálogo. |
| `POST` | `/documents` | Subir un archivo y solicitar su indexación. |
| `GET` | `/documents/{document_id}` | Consultar metadata del documento. |
| `GET` | `/documents/{document_id}/formats` | Consultar estados y formatos generados. |
| `POST` | `/documents/{document_id}/formats/regenerate` | Regenerar uno o varios formatos. |
| `GET` | `/documents/{document_id}/download` | Descargar el archivo original. |

### Carga

`POST /documents` envía `multipart/form-data` con:

- `file`;
- `profile`;
- `niche`;
- `detail_level`;
- `learning_objective` cuando se proporciona.

El navegador establece automáticamente el `Content-Type` y su `boundary`.
Frontend no asigna `document_id`, formatos de salida ni chunks: BackendAPI
identifica el documento, indexa y registra la generación de los cuatro formatos.
La indexación ocurre antes de responder; la generación de formatos continúa en
segundo plano. La respuesta de carga no incluye los contenidos generados.

El cliente maneja como duplicado una respuesta HTTP `200` o `duplicate: true`;
un documento nuevo normalmente se responde con `201`. Después de cargar, el
Centro de capacitación consulta `/formats` para obtener resultados y estados.

### Estados y actualización de formatos

Los estados agregados consumidos por el frontend son `pending`, `processing`,
`ready`, `partial` y `error`. Por formato, la interfaz contempla `pending`,
`processing`, `success`, `failed` y `no_results`.

Mientras la respuesta agregada sea `pending` o `processing`, el Centro de
capacitación consulta `/formats` cada 3,5 segundos. Detiene el polling al
alcanzar `ready`, `partial` o `error`, al cambiar de documento o al salir de esa
vista; también lo pausa tras errores consecutivos.

`ready` es el estado agregado calculado por BackendAPI, no una afirmación de
que el frontend comprueba por sí solo los cuatro formatos. Para `partial` o
`error`, la acción general permite reintentar; cada vista de formato también
puede solicitar regeneración individual. La solicitud de regeneración envía
JSON `{ "formats": [...] }` y recibe los identificadores de los nuevos intentos.

### Errores y timeouts

`ApiError` conserva status, código, mensaje y detalles del servidor. Los
módulos convierten esos errores a mensajes de interfaz mediante
`js/utils/friendlyError.js`, el diálogo de estado y las notificaciones.
Los abortos por timeout se representan como HTTP `408`; errores de red
actualizan el indicador de conexión.

El timeout general es de 30 segundos por defecto. La carga y descarga usan el
timeout de procesamiento, actualmente 120 segundos. El polling de formatos
realiza nuevas consultas al endpoint; no mantiene una conexión en tiempo real.

## Configuración

La plantilla de variables está en `.env.example`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT_MS=30000
```

`VITE_API_BASE_URL` configura la URL base de BackendAPI. El frontend la resuelve
con esta precedencia:

1. variable de entorno Vite `VITE_API_BASE_URL`;
2. `window.__ENV__.VITE_API_BASE_URL` si se inyecta en runtime;
3. query string `?api=...` o `?backend=...`;
4. valor guardado en `localStorage` (`nuevamente_backend_url`);
5. mismo origen en despliegues que no sean `localhost` o `127.0.0.1`;
6. fallback `http://localhost:8000`.

El badge de BackendAPI en el encabezado permite cambiar la URL en el navegador.
También se puede invocar `window.setBackendUrl(url)`; pasar una URL vacía elimina
el valor guardado y vuelve a la resolución por defecto. Los cambios de URL
requieren recargar la página.

`VITE_API_TIMEOUT_MS` define el timeout general en milisegundos. El timeout de
carga/descarga se configura en `js/config.js`.

## Desarrollo y despliegue

Ejecuta estos comandos desde `frontend/`:

```bash
npm ci
npm run dev
```

Vite sirve la aplicación en `http://localhost:3000` y abre el navegador. No
abrir `index.html` directamente con `file://`: la aplicación usa módulos ES.

Scripts disponibles:

| Comando | Resultado |
|---|---|
| `npm run dev` | Servidor local de desarrollo. |
| `npm run build` | Genera el sitio estático en `dist/`. |
| `npm run preview` | Sirve localmente el build de `dist/` para revisión. |

El `Dockerfile` construye la aplicación con Node 20 y la publica con Nginx.
`VITE_API_BASE_URL` y `VITE_API_TIMEOUT_MS` se inyectan durante el build. El
`nginx.conf` sirve la SPA y reenvía `/api/` al servicio `backend:8000`, con un
límite de carga de 10 MiB. El build Docker espera el contexto de construcción
en la raíz del repositorio.

## Pruebas y calidad

`package.json` define scripts para desarrollo, build y preview; no define un
script de test ni de lint. Para validar el empaquetado de producción:

```bash
npm run build
```
