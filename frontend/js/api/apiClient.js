/**
 * apiClient.js
 * Cliente HTTP desacoplado para la comunicación con la API de FastAPI.
 * Maneja respuestas de éxito (200, 201) y errores tipificados (400, 404, 413, 415, 422, 502, 500).
 */

import { CONFIG } from '../config.js';

/**
 * Error personalizado con metadatos HTTP para feedback enriquecido en la UI
 */
export class ApiError extends Error {
  constructor(statusOrMessage, bodyOrStatus = {}, maybeDetail = null) {
    let resolvedStatus = 500;
    let resolvedMessage = '';
    let resolvedCode = '';
    let resolvedDetails = [];
    let rawBody = {};

    // Soporte polimórfico: new ApiError(status, body) o new ApiError(message, status, detail)
    if (typeof statusOrMessage === 'number') {
      resolvedStatus = statusOrMessage;
      rawBody = typeof bodyOrStatus === 'object' && bodyOrStatus !== null ? bodyOrStatus : {};

      if (typeof rawBody.message === 'string' && rawBody.message.trim()) {
        resolvedMessage = rawBody.message;
      } else if (typeof rawBody.detail === 'string' && rawBody.detail.trim()) {
        resolvedMessage = rawBody.detail;
      } else if (Array.isArray(rawBody.detail) && rawBody.detail.length > 0) {
        resolvedMessage = rawBody.detail.map(d => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg}`).join('; ');
        resolvedDetails = rawBody.detail;
      } else if (Array.isArray(rawBody.errors) && rawBody.errors.length > 0) {
        resolvedMessage = rawBody.errors.map(e => `${e.field ? e.field + ': ' : ''}${e.message || e.msg || ''}`).join('; ');
      } else {
        resolvedMessage = ApiError.getDefaultMessageForStatus(resolvedStatus);
      }
      resolvedCode = rawBody.code || ApiError.getDefaultCodeForStatus(resolvedStatus);
      if (rawBody.details) resolvedDetails = rawBody.details;
    } else {
      resolvedMessage = statusOrMessage || 'Error en la petición API';
      resolvedStatus = typeof bodyOrStatus === 'number' ? bodyOrStatus : 500;
      resolvedCode = ApiError.getDefaultCodeForStatus(resolvedStatus);
      resolvedDetails = maybeDetail ? [maybeDetail] : [];
    }

    super(resolvedMessage);
    this.name = 'ApiError';
    this.status = resolvedStatus;
    this.code = resolvedCode;
    this.details = Array.isArray(resolvedDetails) ? resolvedDetails : [resolvedDetails];
    this.timestamp = new Date().toISOString();
    this.rawBody = rawBody;
  }

  static getDefaultCodeForStatus(status) {
    const map = {
      200: 'DOCUMENT_DUPLICATE',
      201: 'DOCUMENT_CREATED',
      400: 'BAD_REQUEST',
      404: 'DOCUMENT_NOT_FOUND',
      408: 'TIMEOUT_ERROR',
      413: 'FILE_TOO_LARGE',
      415: 'UNSUPPORTED_MEDIA_TYPE',
      422: 'REQUEST_VALIDATION_ERROR',
      500: 'INTERNAL_SERVER_ERROR',
      502: 'OCI_STORAGE_ERROR'
    };
    return map[status] || `HTTP_${status}`;
  }

  static getDefaultMessageForStatus(status) {
    const map = {
      200: 'El documento ya existía previamente en el repositorio.',
      201: 'Documento nuevo creado y registrado exitosamente.',
      400: 'Documento inválido o vacío.',
      404: 'Recurso o documento no encontrado.',
      408: 'Tiempo de espera agotado al comunicarse con el servidor (Timeout).',
      413: `El archivo supera el tamaño máximo permitido de ${CONFIG.UPLOAD.MAX_SIZE_MB} MB.`,
      415: 'Formato o MIME type no soportado. Se admiten archivos PDF, Markdown (.md) y TXT.',
      422: 'Error de validación en la estructura del request.',
      502: 'Fallo al almacenar o comunicarse con OCI Object Storage.',
      500: 'Error interno inesperado en el servidor.'
    };
    return map[status] || `Error del servidor HTTP ${status}`;
  }
}

export function mapBackendError(status, detail) {
  return {
    title: ApiError.getDefaultCodeForStatus(status),
    message: detail || ApiError.getDefaultMessageForStatus(status)
  };
}

export const apiClient = {
  /**
   * Verifica la disponibilidad del backend
   */
  async checkHealth() {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.HEALTH}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response.ok;
    } catch {
      clearTimeout(timeoutId);
      return false;
    }
  },

  /**
   * Sube y procesa un documento en el backend usando multipart/form-data (POST /api/v1/documents).
   * Contrato Sprint 2: El backend recibe el archivo junto con parámetros pedagógicos,
   * indexa el documento y genera internamente Quiz + Flashcards.
   *
   * @param {File} file - Archivo PDF, MD o TXT (máx 10 MB)
   * @param {Object} pedagogicalParams - { profile, niche, detail_level, learning_objective }
   */
  async uploadFile(file, pedagogicalParams = {}) {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.UPLOAD_FILE}`;
    const formData = new FormData();
    formData.append('file', file);

    // Parámetros pedagógicos obligatorios y opcionales según contrato
    if (pedagogicalParams) {
      if (pedagogicalParams.profile) {
        formData.append('profile', pedagogicalParams.profile);
      }
      if (pedagogicalParams.niche) {
        formData.append('niche', pedagogicalParams.niche);
      }
      if (pedagogicalParams.detail_level) {
        formData.append('detail_level', pedagogicalParams.detail_level);
      }
      if (pedagogicalParams.learning_objective && typeof pedagogicalParams.learning_objective === 'string' && pedagogicalParams.learning_objective.trim()) {
        formData.append('learning_objective', pedagogicalParams.learning_objective.trim());
      }
    }
    // IMPORTANTE: Front NO debe enviar document_id, formats, output_format ni chunks.
    // IMPORTANTE: NO establecer manualmente el header Content-Type (el navegador añade multipart/form-data con boundary).

    const controller = new AbortController();
    // Timeout extendido para absorver el procesamiento síncrono RAG + LLM si el backend lo ejecuta en el POST
    const timeoutMs = CONFIG.API.ADAPTATIONS_TIMEOUT_MS || 120000;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'application/json'
        },
        body: formData,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const json = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      return {
        ...json,
        httpStatus: response.status,
        isDuplicate: response.status === 200 || Boolean(json.duplicate)
      };
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new ApiError(408, {
          code: 'TIMEOUT_ERROR',
          message: `Tiempo de espera agotado al procesar el archivo (${Math.round(timeoutMs / 1000)}s Timeout).`
        });
      }
      if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
        throw new ApiError(0, {
          code: 'CONNECTION_REFUSED',
          message: `No se pudo conectar con el Backend (FastAPI). Verifica que esté activo en ${CONFIG.API.DEFAULT_BASE_URL}`
        });
      }
      throw err;
    }
  },

  /**
   * Obtiene la lista de documentos persistidos en el backend (GET /api/v1/documents)
   * Diagrama C - Flujo de Consulta desde la Biblioteca (Tarea 6)
   */
  async getDocuments() {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.DOCUMENTS}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const json = await response.json().catch(() => ([]));

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      if (Array.isArray(json)) return json;
      if (Array.isArray(json.items)) return json.items;
      if (Array.isArray(json.documents)) return json.documents;
      return [];
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new ApiError(408, { message: 'Tiempo de espera agotado al consultar los documentos.' });
      }
      if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
        throw new ApiError(0, {
          code: 'CONNECTION_REFUSED',
          message: `No se pudo conectar con el Backend (FastAPI). Verifica que esté activo en ${CONFIG.API.DEFAULT_BASE_URL}`
        });
      }
      throw err;
    }
  },

  /**
   * Consulta la metadata de un documento individual (GET /api/v1/documents/{id})
   */
  async getDocumentById(documentId) {
    const endpoint = typeof CONFIG.API.ENDPOINTS.DOCUMENT_DETAILS === 'function'
      ? CONFIG.API.ENDPOINTS.DOCUMENT_DETAILS(documentId)
      : `/documents/${documentId}`;
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const json = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      return json;
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new ApiError(408, { message: 'Tiempo de espera agotado al consultar el documento.' });
      }
      throw err;
    }
  },

  /**
   * Obtiene los formatos persistidos generados para un documento (GET /api/v1/documents/{id}/formats)
   * Diagrama C - Formatos Quiz y Flashcards (Tarea 7)
   */
  async getDocumentFormats(documentId) {
    const endpoint = typeof CONFIG.API.ENDPOINTS.DOCUMENT_FORMATS === 'function'
      ? CONFIG.API.ENDPOINTS.DOCUMENT_FORMATS(documentId)
      : `/documents/${documentId}/formats`;
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const json = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      return json;
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new ApiError(408, { message: 'Tiempo de espera agotado al consultar los formatos.' });
      }
      throw err;
    }
  },

  /**
   * Llama al endpoint de adaptación pedagógica del Backend (POST /api/v1/adaptations)
   * En Sprint 2 genera automáticamente Quiz + Flashcards a partir del documento indexado.
   * @param {Object} adaptationRequest - { document_id, profile, niche, detail_level, learning_objective }
   */
  async adaptContent(adaptationRequest) {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.ADAPTATIONS}`;
    const timeoutMs = CONFIG.API.ADAPTATIONS_TIMEOUT_MS || 120000;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(adaptationRequest),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const json = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      return {
        ...json,
        httpStatus: response.status
      };
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new ApiError(408, {
          code: 'TIMEOUT_ERROR',
          message: `El servidor tardó más de ${Math.round(timeoutMs / 1000)}s en generar el material de estudio con IA. Intenta nuevamente.`
        });
      }
      if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
        throw new ApiError(0, {
          code: 'CONNECTION_REFUSED',
          message: `No se pudo conectar con el Backend (FastAPI). Verifica que esté activo en ${CONFIG.API.DEFAULT_BASE_URL}`
        });
      }
      throw err;
    }
  }
};
