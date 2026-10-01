/**
 * config.js
 * Constantes de configuración, endpoints de backend desacoplados y valores por defecto.
 * Compatible nativamente con Vite.js (.env) y con servidores estáticos estándar.
 */

/**
 * Resuelve la URL base del Backend FastAPI de forma desacoplada y dinámica:
 * 1. Variable de entorno Vite (import.meta.env.VITE_API_BASE_URL)
 * 2. Inyección global en window.__ENV__?.VITE_API_BASE_URL (despliegues Docker/Nginx)
 * 3. Parámetro en URL (?api=http://... o ?backend=http://...) para QA y testing en caliente
 * 4. LocalStorage ('nuevamente_backend_url') para cambio rápido en navegador
 * 5. Fallback por defecto: 'http://localhost:8000'
 */
function resolveApiBaseUrl() {
  // 1. Variable de entorno de Vite
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
      return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
    }
  } catch {
    // Entorno sin soporte de import.meta.env
  }

  // 2. Inyección externa en runtime (Docker / Servidor)
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.VITE_API_BASE_URL) {
    return window.__ENV__.VITE_API_BASE_URL.replace(/\/+$/, '');
  }

  // 3. Parámetro en URL (?api= o ?backend=)
  if (typeof window !== 'undefined' && window.location) {
    const params = new URLSearchParams(window.location.search);
    const queryUrl = params.get('api') || params.get('backend');
    if (queryUrl) {
      localStorage.setItem('nuevamente_backend_url', queryUrl);
      return queryUrl.replace(/\/+$/, '');
    }

    // 4. LocalStorage
    const storedUrl = localStorage.getItem('nuevamente_backend_url');
    if (storedUrl) {
      return storedUrl.replace(/\/+$/, '');
    }

    // 5. Servidor desplegado (OCI / Docker / Nginx reverse proxy):
    // Si no estamos en localhost, la API es atendida por el mismo host (Nginx en puerto 80)
    if (window.location.hostname && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      return window.location.origin;
    }
  }

  // 6. Fallback por defecto (Desarrollo local)
  return 'http://localhost:8000';
}

function resolveTimeoutMs() {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_TIMEOUT_MS) {
      const parsed = parseInt(import.meta.env.VITE_API_TIMEOUT_MS, 10);
      if (!isNaN(parsed) && parsed > 0) return parsed;
    }
  } catch {}
  return 30000;
}

export const CONFIG = {
  APP_NAME: 'NuevaMente',
  VERSION: '1.0.0',
  HACKATHON: 'ONE · Grupo 10',

  // Configuración de Backend (FastAPI desacoplado)
  API: {
    DEFAULT_BASE_URL: resolveApiBaseUrl(),
    V1_PREFIX: '/api/v1',
    ENDPOINTS: {
      HEALTH: '/health',
      DOCUMENTS: '/documents',
      UPLOAD_FILE: '/documents',
      DOCUMENT_DETAILS: (id) => `/documents/${id}`,
      DOCUMENT_FORMATS: (id) => `/documents/${id}/formats`
    },
    TIMEOUT_MS: resolveTimeoutMs()
  },

  // Restricciones de carga de documentos (Sprint 2: Límite estricto 10 MB)
  UPLOAD: {
    MAX_SIZE_MB: 10,
    ALLOWED_EXTENSIONS: ['pdf', 'md', 'txt']
  },

  // Almacenamiento local
  STORAGE_KEYS: {
    API_MODE: 'nuevamente_api_mode',
    LAST_DOC: 'nuevamente_last_doc',
    BACKEND_URL: 'nuevamente_backend_url'
  }
};

// Helper de consola para QA y desarrolladores: cambiar URL del backend al instante
if (typeof window !== 'undefined') {
  window.setBackendUrl = (url) => {
    if (!url) {
      localStorage.removeItem('nuevamente_backend_url');
      console.log('[Config] Backend URL restablecida al valor por defecto (http://localhost:8000).');
    } else {
      localStorage.setItem('nuevamente_backend_url', url);
      console.log(`[Config] Backend URL actualizada a: ${url}`);
    }
    window.location.reload();
  };
}
