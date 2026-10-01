/**
 * studyHub.js
 * Orquestador principal del Centro de Estudio Multi-Formato.
 */

import { state } from '../state.js';
import { apiClient } from '../api/apiClient.js';
import { flashcards } from './flashcards.js';
import { quiz } from './quiz.js';
import { videoGuide } from './videoGuide.js';
import { summary } from './summary.js';
import { statusDialog } from './statusDialog.js';
import { notifyError, notifySuccess } from './notifications.js';

export const studyHub = {
  elements: {},
  isFetchingFormats: false,

  init() {
    this.bindElements();
    this.setupFormatTabs();
    this.setupActions();

    // Inicializar submódulos
    flashcards.init();
    quiz.init();
    videoGuide.init();
    summary.init();

    // Escuchar cambios de estado
    state.subscribe((s) => {
      this.syncWithState(s);
    });

    this.syncWithState(state.get());
  },

  bindElements() {
    this.elements = {
      topicBadge: document.getElementById('studyTopicBadge'),
      topicTitle: document.getElementById('studyTopicTitle'),
      btnRefreshFormats: document.getElementById('btnRefreshFormats'),
      formatTabs: document.querySelectorAll('.format-tab-btn'),
      formatViews: {
        flashcards: document.getElementById('viewFormatFlashcards'),
        quiz: document.getElementById('viewFormatQuiz'),
        video: document.getElementById('viewFormatVideo'),
        sintesis: document.getElementById('viewFormatSintesis')
      }
    };
  },

  setupActions() {
    if (this.elements.btnRefreshFormats) {
      this.elements.btnRefreshFormats.addEventListener('click', () => {
        const doc = state.get().currentDocument;
        if (doc) {
          this.fetchFormatsForCurrentDocument(doc);
        }
      });
    }
  },

  setupFormatTabs() {
    this.elements.formatTabs.forEach(btn => {
      btn.addEventListener('click', () => {
        const format = btn.getAttribute('data-format');
        state.set({
          studyHub: {
            ...state.get().studyHub,
            activeFormat: format
          }
        });
      });
    });
  },

  syncWithState(s) {
    const { currentDocument, studyHub: hubState } = s;

    // Si no hay documento seleccionado: estado de bienvenida limpio
    if (!currentDocument) {
      if (this.elements.topicBadge) {
        this.elements.topicBadge.textContent = 'BIBLIOTECA';
      }
      if (this.elements.topicTitle) {
        this.elements.topicTitle.textContent = 'Selecciona o sube un documento en La Biblioteca para comenzar a estudiar';
      }
      flashcards.render([]);
      quiz.render(null);
      videoGuide.render(null);
      summary.render(null);
      return;
    }

    const activeSection = this.getActiveSection(currentDocument, hubState.activeSectionId);

    // Actualizar Encabezado del Study Hub
    if (this.elements.topicBadge) {
      this.elements.topicBadge.textContent = currentDocument.discipline || 'MODALIDAD MULTI-FORMATO';
    }
    if (this.elements.topicTitle) {
      this.elements.topicTitle.textContent = activeSection?.title || currentDocument.title;
    }

    // Actualizar Pestañas y Vistas
    const currentFormat = hubState.activeFormat || 'flashcards';

    this.elements.formatTabs.forEach(btn => {
      if (btn.getAttribute('data-format') === currentFormat) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    Object.keys(this.elements.formatViews).forEach(formatKey => {
      const viewEl = this.elements.formatViews[formatKey];
      if (viewEl) {
        if (formatKey === currentFormat) {
          viewEl.classList.add('active');
        } else {
          viewEl.classList.remove('active');
        }
      }
    });

    // Tarea 7 y 8: Resolver formatos generados por Backend (GET /documents/{id}/formats)
    const backendFormats = hubState.formats || {};
    // Actualizar botón de reintento/sincronización de formatos
    if (this.elements.btnRefreshFormats) {
      this.elements.btnRefreshFormats.style.display = (globalStatus === 'error' || globalStatus === 'partial') ? 'inline-flex' : 'none';
    }

    // Auto-recuperar formatos si no están en memoria aún para el documento activo
    if (currentDocument.id && !hubState.formats && hubState.formatsStatus !== 'loading' && hubState.formatsStatus !== 'error' && !this.isFetchingFormats) {
      this.fetchFormatsForCurrentDocument(currentDocument);
    }

    // 1. Flashcards (Tarea 8)
    const flashcardsData = backendFormats.flashcards 
      || activeSection?.flashcards 
      || (backendFormats.cards ? backendFormats.cards : null)
      || (globalStatus === 'processing' ? { status: 'processing' } : null)
      || (globalStatus === 'error' ? { status: 'failed', errorMessage: 'No se pudieron recuperar las Flashcards desde el backend.' } : null);
    flashcards.render(flashcardsData);

    // 2. Quiz (Tarea 8)
    const quizData = backendFormats.quiz 
      || activeSection?.quiz 
      || (backendFormats.questions ? backendFormats.questions : null)
      || (globalStatus === 'processing' ? { status: 'processing' } : null)
      || (globalStatus === 'error' ? { status: 'failed', errorMessage: 'No se pudieron recuperar las preguntas del Quiz desde el backend.' } : null);
    quiz.render(quizData);

    // 3. Tutorial / Video (Extensible)
    const videoData = backendFormats.tutorial 
      || backendFormats.video 
      || activeSection?.video;
    videoGuide.render(videoData);

    // 4. Síntesis / Resumen (Extensible)
    const summaryData = backendFormats.summary 
      || backendFormats.sintesis 
      || activeSection?.sintesis;
    summary.render(summaryData);
  },

  /**
   * Consulta GET /documents/{id}/formats al Backend y sincroniza el estado
   */
  async fetchFormatsForCurrentDocument(doc) {
    if (!doc?.id || this.isFetchingFormats) return;
    this.isFetchingFormats = true;

    try {
      state.set({
        studyHub: {
          ...state.get().studyHub,
          formatsStatus: 'loading'
        }
      });

      const formats = await apiClient.getDocumentFormats(doc.id);
      const resolvedFormats = formats?.formats || formats;
      const globalStatus = formats?.status || (resolvedFormats ? 'ready' : 'empty');

      state.set({
        studyHub: {
          ...state.get().studyHub,
          formats: resolvedFormats,
          formatsStatus: globalStatus
        }
      });

      if (globalStatus === 'ready') {
        notifySuccess('Formatos Sincronizados', 'Se cargaron los materiales pedagógicos desde el Backend.');
      }
    } catch (err) {
      console.warn('[StudyHub] Error al consultar formatos desde el backend:', err.message);
      state.set({
        studyHub: {
          ...state.get().studyHub,
          formatsStatus: 'error'
        }
      });

      statusDialog.showError({
        status: err.status || 500,
        code: err.code || 'FORMATS_FETCH_ERROR',
        message: err.message || `No fue posible cargar los formatos de estudio para "${doc.title || doc.filename}".`,
        details: [`Documento ID: ${doc.id}`, err.message],
        filename: doc.filename || doc.title
      });

      notifyError(`Error en Formatos (${err.status || 500})`, err.message);
    } finally {
      this.isFetchingFormats = false;
    }
  },

  getActiveSection(doc, sectionId) {
    if (!doc || !doc.sections || doc.sections.length === 0) return null;
    if (sectionId) {
      const found = doc.sections.find(s => s.id === sectionId);
      if (found) return found;
    }
    return doc.sections[0];
  }
};
