/**
 * apiClient.js
 * Cliente HTTP desacoplado para la comunicación con la API de FastAPI.
 * Maneja respuestas de éxito (200, 201) y errores tipificados (400, 404, 413, 415, 422, 502, 500).
 */

import { CONFIG } from '../config.js';
import { state } from '../state.js';

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
        resolvedMessage = rawBody.detail.map(d => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg || d.message}`).join('; ');
      } else if (Array.isArray(rawBody.errors) && rawBody.errors.length > 0) {
        resolvedMessage = rawBody.errors.map(e => `${e.field ? e.field + ': ' : ''}${e.message || e.msg || ''}`).join('; ');
      } else {
        resolvedMessage = ApiError.getDefaultMessageForStatus(resolvedStatus);
      }

      // Preservar siempre errors[] (Auditoria.md P2 / S2)
      if (Array.isArray(rawBody.errors) && rawBody.errors.length > 0) {
        resolvedDetails = rawBody.errors;
      } else if (Array.isArray(rawBody.detail) && rawBody.detail.length > 0) {
        resolvedDetails = rawBody.detail;
      } else if (rawBody.details) {
        resolvedDetails = rawBody.details;
      }

      resolvedCode = rawBody.code || ApiError.getDefaultCodeForStatus(resolvedStatus);
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
    this.errors = Array.isArray(rawBody.errors) ? rawBody.errors : [];
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
      408: 'REQUEST_TIMEOUT',
      409: 'DOCUMENT_STATE_CONFLICT',
      413: 'FILE_TOO_LARGE',
      415: 'UNSUPPORTED_MEDIA_TYPE',
      422: 'REQUEST_VALIDATION_ERROR',
      500: 'INTERNAL_SERVER_ERROR',
      502: 'BAD_GATEWAY'
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
      409: 'Conflicto con el estado actual del recurso en el servidor.',
      413: `El archivo supera el tamaño máximo permitido de ${CONFIG.UPLOAD.MAX_SIZE_MB} MB.`,
      415: 'Formato o MIME type no soportado. Se admiten archivos PDF, Markdown (.md) y TXT.',
      422: 'Error de validación en la estructura del request.',
      502: 'Una dependencia externa o servicio de integración no respondió a tiempo.',
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

async function parseResponseBody(response) {
  try {
    const text = await response.text();
    if (!text || !text.trim()) return {};
    return JSON.parse(text);
  } catch {
    return { message: ApiError.getDefaultMessageForStatus(response.status) };
  }
}

function wrapFetchError(err, timeoutMessage) {
  if (err instanceof ApiError) return err;

  if (err && err.name === 'AbortError') {
    return new ApiError(408, {
      code: 'TIMEOUT_ERROR',
      message: timeoutMessage || 'Tiempo de espera agotado al comunicarse con el servidor (Timeout).'
    });
  }

  const isNetwork = err instanceof TypeError ||
    (err && typeof err.message === 'string' && (
      err.message.toLowerCase().includes('fetch') ||
      err.message.toLowerCase().includes('network') ||
      err.message.toLowerCase().includes('failed to fetch') ||
      err.message.toLowerCase().includes('load failed')
    ));

  if (isNetwork) {
    state.set({ isBackendConnected: false, lastConnectionCheck: Date.now() });
    return new ApiError(0, {
      code: 'CONNECTION_REFUSED',
      message: `No se pudo conectar con el Backend (FastAPI). Verifica que esté activo en ${CONFIG.API.DEFAULT_BASE_URL}`
    });
  }

  return new ApiError(500, {
    code: 'CLIENT_ERROR',
    message: err?.message || 'Error inesperado durante la comunicación con el servidor.'
  });
}

export const apiClient = {
  /**
   * Verifica la disponibilidad del Backend mediante GET /api/v1/health y sincroniza el estado global
   * @returns {Promise<boolean>}
   */
  async checkHealth() {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.HEALTH}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      const contentType = response.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json');
      const isConnected = response.ok && isJson;

      state.set({ isBackendConnected: isConnected, lastConnectionCheck: Date.now() });
      return isConnected;
    } catch {
      clearTimeout(timeoutId);
      state.set({ isBackendConnected: false, lastConnectionCheck: Date.now() });
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
    // Timeout extendido para absorver el procesamiento síncrono RAG + LLM en el POST de documentos
    const timeoutMs = CONFIG.API.PROCESSING_TIMEOUT_MS || CONFIG.API.ADAPTATIONS_TIMEOUT_MS || 120000;
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

      const json = await parseResponseBody(response);

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      state.set({ isBackendConnected: true, lastConnectionCheck: Date.now() });

      return {
        ...json,
        httpStatus: response.status,
        isDuplicate: response.status === 200 || Boolean(json.duplicate)
      };
    } catch (err) {
      clearTimeout(timeoutId);
      throw wrapFetchError(err, `Tiempo de espera agotado al procesar el archivo (${Math.round(timeoutMs / 1000)}s Timeout).`);
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

      const json = await parseResponseBody(response);

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      state.set({ isBackendConnected: true, lastConnectionCheck: Date.now() });

      if (Array.isArray(json.documents)) return json.documents;
      if (Array.isArray(json)) return json;
      if (Array.isArray(json.items)) return json.items;

      // Validación estricta de contrato (Auditoria.md Sec 3: P1 / S1)
      throw new ApiError(200, {
        code: 'API_CONTRACT_ERROR',
        message: 'La respuesta de documentos no cumple con el contrato esperado ({ documents: [...] }).'
      });
    } catch (err) {
      clearTimeout(timeoutId);
      throw wrapFetchError(err, 'Tiempo de espera agotado al consultar los documentos.');
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

      const json = await parseResponseBody(response);

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      state.set({ isBackendConnected: true, lastConnectionCheck: Date.now() });
      return json;
    } catch (err) {
      clearTimeout(timeoutId);
      throw wrapFetchError(err, 'Tiempo de espera agotado al consultar el documento.');
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

      const json = await parseResponseBody(response);

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      // Validación estricta de contrato (Auditoria.md Sec 5)
      if (!json || typeof json !== 'object' || (!json.status && !json.formats)) {
        throw new ApiError(200, {
          code: 'API_CONTRACT_ERROR',
          message: 'La respuesta de formatos no cumple con la estructura esperada por el cliente ({ status, formats }).'
        });
      }

      state.set({ isBackendConnected: true, lastConnectionCheck: Date.now() });
      return json;
    } catch (err) {
      clearTimeout(timeoutId);
      throw wrapFetchError(err, 'Tiempo de espera agotado al consultar los formatos.');
    }
  },

  /**
   * Solicita la regeneración asíncrona de formatos educativos (POST /api/v1/documents/{id}/formats/regenerate)
   * Backend responde 202 Accepted con status 'processing' y nuevos format_id.
   * @param {string} documentId - ID del documento
   * @param {Array<string>} formats - Formatos a regenerar (ej. ['quiz'], ['flashcards'] o ['quiz', 'flashcards'])
   * @returns {Promise<Object>}
   */
  async regenerateFormats(documentId, formats) {
    if (!documentId) throw new Error('ID de documento requerido para regenerar.');
    if (!Array.isArray(formats) || formats.length === 0) {
      throw new Error('Debe indicarse al menos un formato para regenerar.');
    }

    const endpoint = typeof CONFIG.API.ENDPOINTS.DOCUMENT_REGENERATE === 'function'
      ? CONFIG.API.ENDPOINTS.DOCUMENT_REGENERATE(documentId)
      : `/documents/${documentId}/formats/regenerate`;
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ formats }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      const json = await parseResponseBody(response);

      if (!response.ok) {
        throw new ApiError(response.status, json);
      }

      // Validación estricta del contrato 202 Accepted de regeneración (PR #62 / Backend #61)
      if (!json || typeof json !== 'object' || !json.document_id || !json.formats || typeof json.formats !== 'object') {
        throw new ApiError(200, {
          code: 'API_CONTRACT_ERROR',
          message: 'La respuesta de regeneración no cumple con la estructura esperada ({ document_id, status, formats }).'
        });
      }

      // El identificador format_id es canónico de Backend y forma parte obligatoria del contrato.
      // Una respuesta sin format_id para los formatos solicitados se trata como incumplimiento (API_CONTRACT_ERROR).
      for (const fmt of formats) {
        const attempt = json.formats[fmt];
        if (!attempt || typeof attempt !== 'object' || !attempt.format_id || typeof attempt.format_id !== 'string') {
          throw new ApiError(200, {
            code: 'API_CONTRACT_ERROR',
            message: `El backend no devolvió el identificador canónico 'format_id' para el formato '${fmt}' en la respuesta de regeneración.`
          });
        }
      }

      state.set({ isBackendConnected: true, lastConnectionCheck: Date.now() });
      return json;
    } catch (err) {
      clearTimeout(timeoutId);
      throw wrapFetchError(err, 'Tiempo de espera agotado al solicitar la regeneración de formatos.');
    }
  },

  /**
   * Descarga el archivo original persistido para un documento desde OCI Object Storage (GET /api/v1/documents/{id}/download)
   * Recupera los bytes binarios y desencadena la descarga de archivo nativa en el navegador del cliente.
   * @param {string} documentId - ID del documento
   * @param {string} [fallbackFilename] - Nombre por defecto del archivo si no está en Content-Disposition
   * @returns {Promise<{ success: boolean, filename: string }>}
   */
  async downloadDocument(documentId, fallbackFilename = 'documento_original') {
    if (!documentId) throw new Error('ID de documento requerido para descargar.');

    const endpoint = typeof CONFIG.API.ENDPOINTS.DOCUMENT_DOWNLOAD === 'function'
      ? CONFIG.API.ENDPOINTS.DOCUMENT_DOWNLOAD(documentId)
      : `/documents/${documentId}/download`;
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT_MS || 30000);

    try {
      const response = await fetch(url, {
        method: 'GET',
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const json = await parseResponseBody(response);
        throw new ApiError(response.status, json);
      }

      // Extraer nombre de archivo desde Content-Disposition si está disponible
      let filename = fallbackFilename;
      const disposition = response.headers.get('content-disposition');
      if (disposition) {
        const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i);
        if (match && match[1]) {
          filename = decodeURIComponent(match[1].trim());
        }
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);

      state.set({ isBackendConnected: true, lastConnectionCheck: Date.now() });
      return { success: true, filename };
    } catch (err) {
      clearTimeout(timeoutId);
      throw wrapFetchError(err, 'Tiempo de espera agotado al descargar el archivo original.');
    }
  }
};
