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
    if (!currentDocument) return;

    const activeSection = this.getActiveSection(currentDocument, hubState.activeSectionId);
    if (!activeSection) return;

    // Actualizar Encabezado del Study Hub
    if (this.elements.topicBadge) {
      this.elements.topicBadge.textContent = currentDocument.discipline || 'MODALIDAD MULTI-FORMATO';
    }
    if (this.elements.topicTitle) {
      this.elements.topicTitle.textContent = activeSection.title;
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

    // Renderizar contenidos del formato
    flashcards.render(activeSection.flashcards);
    quiz.render(activeSection.quiz);
    videoGuide.render(activeSection.video);
    summary.render(activeSection.sintesis);
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
