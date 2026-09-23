/**
 * state.js
 * Almacén central de estado reactivo para NuevaMente.
 * Implementa el patrón Observable para notificar a los módulos sobre cambios de estado.
 */

import { sampleLibrary } from './data/sampleLibrary.js';
import { CONFIG } from './config.js';

// Documento por defecto cargado inicialmente
const initialSampleKey = 'cloud_architecture';
const initialDocument = sampleLibrary[initialSampleKey];

const internalState = {
  // Navegación principal: 'library' | 'upload' | 'notebook' | 'study'
  activeTab: 'library',

  // Modo de API: 'mock' | 'real'
  apiMode: localStorage.getItem(CONFIG.STORAGE_KEYS.API_MODE) || 'mock',

  // Archivo seleccionado por el usuario en la pestaña de carga
  selectedFile: {
    name: initialDocument.filename,
    size: initialDocument.filesize,
    format: initialDocument.filename.split('.').pop().toUpperCase(),
    sampleKey: initialSampleKey,
    rawFile: null
  },

  // Documento activo procesado por el pipeline RAG
  currentDocument: {
    id: initialDocument.id,
    title: initialDocument.title,
    discipline: initialDocument.discipline,
    description: initialDocument.description,
    filename: initialDocument.filename,
    filesize: initialDocument.filesize,
    metadatos: initialDocument.metadatos,
    sections: initialDocument.sections
  },

  // Libros y documentos personalizados subidos por el usuario durante la sesión
  customBooks: [],

  // Parámetros de adaptación seleccionados (contrato v1)
  adaptationParams: {
    target_profile: 'intermediate',
    output_format: 'all',
    niche_context: 'general'
  },

  // Estado del Cuaderno Interactivo Dinámico
  notebook: {
    currentSpreadIndex: 0, // 0: Portada, 1+: Spreads de secciones, Último: Índice
    isTurningPage: false
  },

  // Estado del Hub de Estudio Multi-formato
  studyHub: {
    activeSectionId: initialDocument.sections[0]?.id || null,
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
