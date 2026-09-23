/**
 * apiClient.js
 * Cliente HTTP desacoplado para la comunicación con la API de FastAPI.
 */

import { CONFIG } from '../config.js';

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

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Error del servidor HTTP ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new Error('Tiempo de espera agotado al subir el archivo (Timeout).');
      }
      throw err;
    }
  },

  /**
   * Llama al endpoint de procesamiento RAG adaptativo
   * @param {Object} adaptationRequest 
   */
  async adaptContent(adaptationRequest) {
    // Intenta primero el endpoint con prefijo v1 o directo según configuración
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
        throw new Error(errJson.detail || `Error al procesar el documento (${response.status})`);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new Error('El servidor tardó demasiado tiempo en responder (Timeout).');
      }
      throw err;
    }
  }
};
