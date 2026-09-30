/**
 * studyHub.js
 * Orquestador principal del Centro de Estudio Multi-Formato.
 */

import { state } from '../state.js';
import { flashcards } from './flashcards.js';
import { quiz } from './quiz.js';
import { videoGuide } from './videoGuide.js';
import { summary } from './summary.js';

export const studyHub = {
  elements: {},

  init() {
    this.bindElements();
    this.setupFormatTabs();

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
      formatTabs: document.querySelectorAll('.format-tab-btn'),
      formatViews: {
        flashcards: document.getElementById('viewFormatFlashcards'),
        quiz: document.getElementById('viewFormatQuiz'),
        video: document.getElementById('viewFormatVideo'),
        sintesis: document.getElementById('viewFormatSintesis')
      }
    };
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

    // 1. Flashcards (Tarea 8)
    const flashcardsData = backendFormats.flashcards 
      || activeSection?.flashcards 
      || (backendFormats.cards ? backendFormats.cards : null);
    flashcards.render(flashcardsData);

    // 2. Quiz (Tarea 8)
    const quizData = backendFormats.quiz 
      || activeSection?.quiz 
      || (backendFormats.questions ? backendFormats.questions : null);
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

  getActiveSection(doc, sectionId) {
    if (!doc || !doc.sections || doc.sections.length === 0) return null;
    if (sectionId) {
      const found = doc.sections.find(s => s.id === sectionId);
      if (found) return found;
    }
    return doc.sections[0];
  }
};
