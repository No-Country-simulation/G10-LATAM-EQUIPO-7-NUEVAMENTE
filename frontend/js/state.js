/**
 * state.js
 * Almacén central de estado reactivo para NuevaMente.
 * Implementa el patrón Observable para notificar a los módulos sobre cambios de estado.
 */

import { CONFIG } from './config.js';

function loadCustomBooksFromStorage() {
  try {
    const raw = localStorage.getItem('nuevamente_custom_books');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch {}
  return [];
}

const internalState = {
  // Navegación principal: 'library' | 'upload' | 'study'
  activeTab: 'library',

  // Modo de API: Exclusivo Backend Real ('real') para Sprint 2
  apiMode: 'real',

  // Archivo seleccionado por el usuario en la pestaña de carga
  selectedFile: null,

  // Documento activo seleccionado o procesado
  currentDocument: null,

  // Libros y documentos personalizados subidos por el usuario
  customBooks: loadCustomBooksFromStorage(),

  // Parámetros de adaptación seleccionados (contrato Sprint 2)
  adaptationParams: {
    profile: 'intermediate',
    niche: 'general',
    detail_level: 'detailed',
    learning_objective: null,
    // Compatibilidad retroactiva con vistas existentes
    target_profile: 'intermediate',
    niche_context: 'general'
  },

  // Estado del Cuaderno Interactivo Dinámico
  notebook: {
    currentSpreadIndex: 0,
    isTurningPage: false
  },

  // Estado del Hub de Estudio Multi-formato
  studyHub: {
    activeSectionId: null,
    formats: null, // Formatos cargados desde GET /documents/{id}/formats
    formatsStatus: 'idle', // 'idle' | 'pending' | 'processing' | 'ready' | 'partial' | 'error'
    activeFormat: 'flashcards', // 'flashcards', 'quiz', 'video', 'sintesis'
    currentCardIndex: 0,
    isFlipped: false
  },

  // Estado del Pipeline RAG
  pipeline: {
    isProcessing: false,
    currentStep: 0,
    statusText: 'Listo para procesar',
    lastLog: 'Sistema RAG inicializado y en espera.'
  },

  // Último JSON estructurado generado
  lastStructuredJson: null
};

// Lista de oyentes suscritos a cambios
const listeners = new Set();

export const state = {
  /**
   * Obtiene una copia inmutable o referencia del estado actual
   */
  get() {
    return internalState;
  },

  /**
   * Actualiza el estado parcialmente y notifica a los observadores
   * @param {Object} partialState 
   */
  set(partialState) {
    Object.assign(internalState, partialState);
    if (partialState.customBooks) {
      try {
        localStorage.setItem('nuevamente_custom_books', JSON.stringify(partialState.customBooks));
      } catch {}
    }
    this.notify();
  },

  /**
   * Suscribe una función callback para ser ejecutada al cambiar el estado
   * @param {Function} listener 
   * @returns {Function} Función para desuscribirse
   */
  subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  /**
   * Notifica a todos los escuchadores registrados
   */
  notify() {
    for (const listener of listeners) {
      try {
        listener(internalState);
      } catch (err) {
        console.error('[State Listener Error]:', err);
      }
    }
  }
};
