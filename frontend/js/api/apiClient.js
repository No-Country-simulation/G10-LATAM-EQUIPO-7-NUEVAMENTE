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
  constructor(message, status = 0, detail = null, raw = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.raw = raw;
  }
}

/**
 * Mapea códigos de estado y detalles del backend a explicaciones claras para el usuario
 * @param {number} status
 * @param {any} detail
 * @returns {{ title: string, message: string }}
 */
export function mapBackendError(status, detail) {
  let friendlyDetail = '';

  if (Array.isArray(detail)) {
    friendlyDetail = detail
      .map(d => `${d.loc ? d.loc.slice(1).join('.') + ': ' : ''}${d.msg}`)
      .join('; ');
  } else if (typeof detail === 'string') {
    friendlyDetail = detail;
  }

  switch (status) {
    case 400:
      return {
        title: 'Documento Inválido (400)',
        message: friendlyDetail || 'El documento está vacío o no contiene texto legible.'
      };
    case 404:
      return {
        title: 'Recurso No Encontrado (404)',
        message: friendlyDetail || 'No se encontró el documento o formato solicitado en el servidor.'
      };
    case 413:
      return {
        title: 'Archivo Demasiado Grande (413)',
        message: friendlyDetail || `El archivo supera el tamaño máximo permitido de ${CONFIG.UPLOAD.MAX_SIZE_MB} MB.`
      };
    case 415:
      return {
        title: 'Formato No Soportado (415)',
        message: friendlyDetail || 'Formato o tipo MIME no admitido. Se admiten archivos PDF, Markdown (.md) y TXT.'
      };
    case 422:
      return {
        title: 'Error de Validación (422)',
        message: friendlyDetail || 'Los parámetros enviados no cumplen con el formato esperado por el backend.'
      };
    case 502:
      return {
        title: 'Fallo de Almacenamiento OCI (502)',
        message: friendlyDetail || 'El documento fue registrado pero no pudo almacenarse en Oracle Cloud (OCI).'
      };
    case 500:
      return {
        title: 'Error Interno del Servidor (500)',
        message: friendlyDetail || 'Ocurrió un error inesperado en el servidor backend al procesar la solicitud.'
      };
    case 408:
      return {
        title: 'Tiempo de Espera Agotado (Timeout)',
        message: 'El servidor tardó más de 30 segundos en responder.'
      };
    case 0:
      return {
        title: 'Error de Conexión',
        message: 'No se pudo conectar con el Backend (FastAPI). Verifica que esté activo en ' + CONFIG.API.DEFAULT_BASE_URL
      };
    default:
      return {
        title: `Error del Servidor (${status || 'Desconocido'})`,
        message: friendlyDetail || `Error en la solicitud HTTP (${status}).`
      };
  }
}

export const apiClient = {
  /**
   * Verifica la disponibilidad del backend
   */
  async checkHealth() {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.HEALTH}`;
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  /**
   * Sube un archivo al backend usando multipart/form-data
   * Maneja: 201 (nuevo), 200 (duplicado), 400, 413, 415, 422, 502, 500
   * @param {File} file 
   */
  async uploadFile(file) {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.UPLOAD_FILE}`;
    const formData = new FormData();
    formData.append('file', file);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      // Si no es OK (códigos >= 400)
      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        const mapped = mapBackendError(response.status, errJson.detail);
        throw new ApiError(mapped.message, response.status, errJson.detail, errJson);
      }

      const data = await response.json();

      // Enriquecer respuesta con estado HTTP para distinguir 201 (nuevo) de 200 (duplicado)
      return {
        ...data,
        httpStatus: response.status,
        isDuplicate: response.status === 200 || Boolean(data.duplicate)
      };
    } catch (err) {
      if (err.name === 'AbortError') {
        const mapped = mapBackendError(408);
        throw new ApiError(mapped.message, 408);
      }
      if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
        const mapped = mapBackendError(0);
        throw new ApiError(mapped.message, 0);
      }
      throw err;
    }
  },

  /**
   * Llama al endpoint de procesamiento RAG adaptativo
   * @param {Object} adaptationRequest 
   */
  async adaptContent(adaptationRequest) {
    const url = `${CONFIG.API.DEFAULT_BASE_URL}${CONFIG.API.V1_PREFIX}${CONFIG.API.ENDPOINTS.ADAPT_RAG}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT_MS);

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

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        const mapped = mapBackendError(response.status, errJson.detail);
        throw new ApiError(mapped.message, response.status, errJson.detail, errJson);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'AbortError') {
        const mapped = mapBackendError(408);
        throw new ApiError(mapped.message, 408);
      }
      if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
        const mapped = mapBackendError(0);
        throw new ApiError(mapped.message, 0);
      }
      throw err;
    }
  }
};
