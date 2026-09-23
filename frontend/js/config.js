/**
 * config.js
 * Constantes de configuración, endpoints de backend y valores por defecto.
 */

export const CONFIG = {
  APP_NAME: 'NuevaMente',
  VERSION: '1.0.0',
  HACKATHON: 'ONE · Grupo 10',

  // Configuración de Backend (FastAPI)
  API: {
    DEFAULT_BASE_URL: 'http://localhost:8000',
    V1_PREFIX: '/api/v1',
    ENDPOINTS: {
      HEALTH: '/health',
      UPLOAD_FILE: '/documents',
      ADAPT_RAG: '/adaptations' // Endpoint de pipeline RAG (contrato v1)
    },
    TIMEOUT_MS: 30000
  },

  // Restricciones de carga de documentos
  UPLOAD: {
    MAX_SIZE_MB: 25,
    ALLOWED_EXTENSIONS: ['pdf', 'md', 'txt']
  },

  // Almacenamiento local
  STORAGE_KEYS: {
    API_MODE: 'nuevamente_api_mode',
    LAST_DOC: 'nuevamente_last_doc'
  }
};
