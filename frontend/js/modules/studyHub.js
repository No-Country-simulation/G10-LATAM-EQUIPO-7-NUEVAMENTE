/**
 * studyHub.js
 * Orquestador principal del Centro de Estudio Multi-Formato.
 * Implementa polling reactivo automático para formatos en estado 'processing'
 * y manejo de estados reales de backend con opciones de reintento ante fallos.
 */

import { state } from '../state.js';
import { apiClient, ApiError } from '../api/apiClient.js';
import { flashcards } from './flashcards.js';
import { quiz } from './quiz.js';
import { videoGuide } from './videoGuide.js';
import { summary } from './summary.js';
import { statusDialog } from './statusDialog.js';
import { notifyError, notifyWarning, notifySuccess } from './notifications.js';
import { toFriendlyError } from '../utils/friendlyError.js';

export const studyHub = {
  elements: {},
  isFetchingFormats: false,
  pollingTimer: null,
  currentPollingDocId: null,

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
      btnDownloadStudyDoc: document.getElementById('btnDownloadStudyDoc'),
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
      this.elements.btnRefreshFormats.addEventListener('click', async () => {
        const doc = state.get().currentDocument;
        if (doc && !this.isFetchingFormats) {
          const currentStatus = state.get().studyHub?.formatsStatus;
          if (currentStatus === 'processing' || currentStatus === 'pending') return; // En polling activo, no enviar reintentos concurrentes
          await this.triggerRegeneration();
        }
      });
    }

    if (this.elements.btnDownloadStudyDoc) {
      this.elements.btnDownloadStudyDoc.addEventListener('click', async () => {
        const doc = state.get().currentDocument;
        if (!doc?.id) return;
        try {
          this.elements.btnDownloadStudyDoc.disabled = true;
          notifySuccess('Iniciando Descarga', 'Recuperando archivo original desde el servidor...');
          await apiClient.downloadDocument(doc.id, doc.filename || doc.title || 'documento_original');
        } catch (err) {
          const friendly = toFriendlyError(err);
          notifyError(friendly.title, friendly.message);
        } finally {
          this.elements.btnDownloadStudyDoc.disabled = false;
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

  /**
   * Actualiza el botón de la cabecera del Centro de Estudio según el estado real de los formatos
   * Renderizado 100% seguro con textContent y nodos del DOM (cero innerHTML con datos dinámicos).
   */
  updateHeaderButtonUI(globalStatus) {
    const btn = this.elements.btnRefreshFormats;
    if (!btn) return;

    btn.textContent = ''; // Limpieza segura

    if (globalStatus === 'processing' || globalStatus === 'pending' || this.isFetchingFormats) {
      btn.style.display = 'inline-flex';
      btn.disabled = true;
      btn.className = 'btn-refresh-formats is-syncing';
      btn.title = 'Los formatos se están generando en segundo plano en el servidor...';

      const icon = document.createElement('span');
      icon.className = 'spin-icon';
      icon.textContent = '↻';

      const label = document.createElement('span');
      label.style.marginLeft = '0.35rem';
      label.textContent = globalStatus === 'pending' ? 'Generación pendiente...' : 'Generando formatos...';

      btn.appendChild(icon);
      btn.appendChild(label);
    } else if (globalStatus === 'partial' || globalStatus === 'error') {
      btn.style.display = 'inline-flex';
      btn.disabled = false;
      btn.className = 'btn-refresh-formats btn-retry-highlight';
      btn.title = globalStatus === 'partial'
        ? 'Uno de los formatos falló. Haz clic para regenerar solo el formato que presentó fallo.'
        : 'La generación de formatos presentó fallos. Haz clic para reintentar la regeneración.';

      const label = document.createElement('span');
      label.textContent = 'Reintentar Formatos';

      btn.appendChild(label);
    } else if (globalStatus === 'ready') {
      btn.style.display = 'inline-flex';
      btn.disabled = false;
      btn.className = 'btn-refresh-formats';
      btn.title = 'Haz clic para regenerar todos los módulos de capacitación a demanda.';

      const icon = document.createElement('span');
      icon.textContent = '↻';

      const label = document.createElement('span');
      label.style.marginLeft = '0.35rem';
      label.textContent = 'Regenerar Módulos';

      btn.appendChild(icon);
      btn.appendChild(label);
    } else {
      btn.style.display = 'none';
      btn.disabled = false;
      btn.className = 'btn-refresh-formats';
    }
  },

  /**
   * Inicia el sondeo (polling) reactivo periódico cada 3.5 segundos mientras los formatos estén en 'processing'/'pending'
   * Controla errores consecutivos para evitar peticiones infinitas ante caída de servidor (Auditoria.md Sec 5: S3).
   */
  startPolling(docId) {
    if (this.pollingTimer && this.currentPollingDocId === docId) {
      return; // Polling ya en curso para este documento
    }

    this.stopPolling();
    this.currentPollingDocId = docId;
    this.consecutivePollingErrors = 0;

    this.pollingTimer = setInterval(async () => {
      const s = state.get();
      const currentDoc = s.currentDocument;

      // Parada y limpieza si el usuario cambió de documento o navegó fuera del Centro de Estudio
      if (!currentDoc || currentDoc.id !== docId || s.activeTab !== 'study') {
        this.stopPolling();
        return;
      }

      if (this.isFetchingFormats) return;

      try {
        const formatsResponse = await apiClient.getDocumentFormats(docId);
        this.consecutivePollingErrors = 0; // Reset ante éxito

        const resolvedFormats = formatsResponse?.formats || formatsResponse;
        const globalStatus = formatsResponse?.status || (resolvedFormats ? 'ready' : 'empty');

        state.set({
          studyHub: {
            ...state.get().studyHub,
            formats: resolvedFormats,
            formatsStatus: globalStatus
          }
        });

        // Parada automática cuando Backend resuelve en estado terminal
        if (globalStatus === 'ready' || globalStatus === 'partial' || globalStatus === 'error') {
          this.stopPolling();

          if (globalStatus === 'ready') {
            notifySuccess('Formatos Listos', '¡Los formatos pedagógicos ya están disponibles para estudiar!');

            // Refrescar metadatos pedagógicos generados por Backend (PR #63)
            apiClient.getDocumentById(docId).then(docDetail => {
              if (docDetail?.learning_metadata) {
                const s = state.get();
                if (s.currentDocument?.id === docId) {
                  state.set({
                    currentDocument: {
                      ...s.currentDocument,
                      learning_metadata: docDetail.learning_metadata,
                      key_concepts: docDetail.learning_metadata.key_concepts || s.currentDocument.key_concepts,
                      prerequisites: docDetail.learning_metadata.prerequisites || s.currentDocument.prerequisites,
                      estimated_time_minutes: docDetail.learning_metadata.estimated_time_minutes ?? s.currentDocument.estimated_time_minutes,
                      summary: docDetail.summary || s.currentDocument.summary
                    }
                  });
                }
              }
            }).catch(() => {});
          } else if (globalStatus === 'partial') {
            notifyWarning('Generación Parcial', 'Uno de los formatos se completó, pero el otro presentó un fallo. Puedes regenerarlo.');
          } else if (globalStatus === 'error') {
            notifyError('Fallo en Formatos', 'No fue posible generar los formatos pedagógicos.');
          }
        }
      } catch (err) {
        this.consecutivePollingErrors = (this.consecutivePollingErrors || 0) + 1;
        console.warn(`[StudyHub Polling] Inconveniente al consultar formatos (${this.consecutivePollingErrors}/3):`, err.message);

        // Detener sondeo ante 404, 400 o 3 fallos consecutivos de red/servidor (Auditoria.md Sec 5: S3)
        if (err.status === 404 || err.status === 400 || this.consecutivePollingErrors >= 3) {
          this.stopPolling();
          state.set({
            studyHub: {
              ...state.get().studyHub,
              formatsStatus: 'error'
            }
          });
          if (this.consecutivePollingErrors >= 3) {
            notifyWarning('Sondeo Pausado', 'No fue posible actualizar el estado tras varios intentos. Puedes reintentar cuando el servidor esté accesible.');
          }
        }
      }
    }, 3500);
  },

  /**
   * Detiene el sondeo reactivo y libera el temporizador
   */
  stopPolling() {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
    this.currentPollingDocId = null;
    this.consecutivePollingErrors = 0;
  },

  /**
   * Dispara la regeneración real de formatos educativos (POST /documents/{id}/formats/regenerate).
   * La regeneración NO debe entenderse como una funcionalidad limitada a escenarios 'partial'
   * ni exclusivamente a formatos fallidos: Backend permite solicitar uno o varios formatos y Front
   * decide cuáles enviar según el flujo y la acción del usuario.
   * Que actualmente en 'partial' el botón general reintente los formatos fallidos se mantiene como
   * comportamiento de UX, pero no como restricción del contrato (PR #62).
   * @param {Array<string>|null} explicitFormats - Formatos específicos a regenerar (ej. ['quiz'])
   */
  async triggerRegeneration(explicitFormats = null) {
    const doc = state.get().currentDocument;
    if (!doc?.id || this.isFetchingFormats) return;

    const hubState = state.get().studyHub || {};
    const currentFormats = hubState.formats || {};
    const globalStatus = hubState.formatsStatus;

    if (globalStatus === 'processing') {
      notifyWarning('Generación en Curso', 'Los formatos ya se están procesando en segundo plano.');
      return;
    }

    let formatsToRegenerate = [];

    if (Array.isArray(explicitFormats) && explicitFormats.length > 0) {
      formatsToRegenerate = explicitFormats;
    } else if (globalStatus === 'partial') {
      // Comportamiento de conveniencia UX: reintentar formatos que presentaron fallo
      ['quiz', 'flashcards', 'tldr', 'video_script'].forEach(fmt => {
        if (currentFormats[fmt]?.status === 'failed' || currentFormats[fmt]?.status === 'no_results') {
          formatsToRegenerate.push(fmt);
        }
      });
      if (formatsToRegenerate.length === 0) {
        formatsToRegenerate = ['quiz', 'flashcards', 'tldr', 'video_script'];
      }
    } else {
      formatsToRegenerate = ['quiz', 'flashcards', 'tldr', 'video_script'];
    }

    this.isFetchingFormats = true;
    this.updateHeaderButtonUI('processing');

    try {
      const response = await apiClient.regenerateFormats(doc.id, formatsToRegenerate);

      // Mergear nuevos intentos canónicos devueltos por Backend (202 Accepted) y arrancar polling.
      // El format_id es canónico de Backend y obligatorio por contrato; no se genera localmente (PR #62).
      const updatedFormats = { ...currentFormats };
      formatsToRegenerate.forEach(fmt => {
        const attempt = response?.formats?.[fmt];
        if (!attempt?.format_id) {
          throw new ApiError(200, {
            code: 'API_CONTRACT_ERROR',
            message: `El backend no devolvió el identificador canónico 'format_id' para el formato '${fmt}'.`
          });
        }
        updatedFormats[fmt] = {
          format_id: attempt.format_id,
          status: attempt.status || 'processing',
          content: null,
          error_message: null
        };
      });

      state.set({
        studyHub: {
          ...state.get().studyHub,
          formats: updatedFormats,
          formatsStatus: 'processing'
        }
      });

      notifySuccess('Regeneración Solicitada', `Se inició un nuevo intento para: ${formatsToRegenerate.join(', ')}.`);
      this.startPolling(doc.id);
    } catch (err) {
      console.warn('[StudyHub] Error al solicitar regeneración:', err);
      const friendly = toFriendlyError(err);

      // Auditoria.md Sec 6: S4 -> Si 409 FORMAT_REGENERATION_IN_PROGRESS, continuar polling
      if (err.status === 409 && (err.code === 'FORMAT_REGENERATION_IN_PROGRESS' || friendly.code === 'FORMAT_REGENERATION_IN_PROGRESS')) {
        notifyWarning(friendly.title, friendly.message);
        this.startPolling(doc.id);
      } else {
        statusDialog.showError({
          status: friendly.status,
          code: friendly.code,
          message: friendly.message,
          details: err.details || [`Documento ID: ${doc.id}`, friendly.message],
          filename: doc.filename || doc.title
        });
        notifyError(friendly.title, friendly.message);
      }
    } finally {
      this.isFetchingFormats = false;
      const currentGlobalStatus = state.get().studyHub?.formatsStatus || 'ready';
      this.updateHeaderButtonUI(currentGlobalStatus);
    }
  },

  syncWithState(s) {
    const { currentDocument, studyHub: hubState, activeTab } = s;

    // Si el usuario navegó fuera del Centro de Estudio, pausar sondeo para ahorrar recursos
    if (activeTab !== 'study') {
      this.stopPolling();
      return;
    }

    // Si no hay documento seleccionado: estado de bienvenida limpio
    if (!currentDocument) {
      this.stopPolling();
      if (this.elements.topicBadge) {
        this.elements.topicBadge.textContent = 'CATÁLOGO';
      }
      if (this.elements.topicTitle) {
        this.elements.topicTitle.textContent = 'Selecciona o carga un documento en el Catálogo de Capacitaciones para comenzar';
      }
      if (this.elements.btnRefreshFormats) {
        this.elements.btnRefreshFormats.style.display = 'none';
      }
      if (this.elements.btnDownloadStudyDoc) {
        this.elements.btnDownloadStudyDoc.style.display = 'none';
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

    // Mostrar u ocultar botón de descarga de documento original
    if (this.elements.btnDownloadStudyDoc) {
      this.elements.btnDownloadStudyDoc.style.display = currentDocument?.id ? 'inline-flex' : 'none';
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

    const backendFormats = hubState.formats || {};
    const globalStatus = hubState.formatsStatus || 'ready';

    // Actualizar botón de Reintentar / Sincronizar
    this.updateHeaderButtonUI(globalStatus);

    // Gestión del Polling Reactivo según estado global (incluye pending, Auditoria.md Sec 5: S4)
    if ((globalStatus === 'processing' || globalStatus === 'pending') && currentDocument.id) {
      this.startPolling(currentDocument.id);
    } else if (globalStatus !== 'processing' && globalStatus !== 'pending') {
      this.stopPolling();
    }

    // Auto-recuperar formatos si no están en memoria aún para el documento activo
    if (currentDocument.id && !hubState.formats && hubState.formatsStatus !== 'loading' && hubState.formatsStatus !== 'error' && !this.isFetchingFormats) {
      this.fetchFormatsForCurrentDocument(currentDocument);
    }

    // 1. Flashcards: pasar datos reales o estado por formato
    const flashcardsData = backendFormats.flashcards 
      || activeSection?.flashcards 
      || (backendFormats.cards ? backendFormats.cards : null)
      || (globalStatus === 'processing' || globalStatus === 'pending' || globalStatus === 'loading' ? { status: globalStatus === 'pending' ? 'pending' : 'processing' } : null)
      || (globalStatus === 'error' ? { status: 'failed', errorMessage: 'No fue posible generar las Tarjetas de Refuerzo.' } : null);
    flashcards.render(flashcardsData);

    // 2. Quiz: pasar datos reales o estado por formato
    const quizData = backendFormats.quiz 
      || activeSection?.quiz 
      || (backendFormats.questions ? backendFormats.questions : null)
      || (globalStatus === 'processing' || globalStatus === 'pending' || globalStatus === 'loading' ? { status: globalStatus === 'pending' ? 'pending' : 'processing' } : null)
      || (globalStatus === 'error' ? { status: 'failed', errorMessage: 'No fue posible generar la Evaluación de Competencias (Quiz).' } : null);
    quiz.render(quizData);

    // 3. Guion Audiovisual Formativo (Video Script)
    const videoData = backendFormats.video_script
      || backendFormats.tutorial 
      || backendFormats.video 
      || activeSection?.video
      || (globalStatus === 'processing' || globalStatus === 'pending' || globalStatus === 'loading' ? { status: globalStatus === 'pending' ? 'pending' : 'processing' } : null)
      || (globalStatus === 'error' ? { status: 'failed', errorMessage: 'No fue posible generar el Guion Audiovisual Formativo.' } : null);
    videoGuide.render(videoData);

    // 4. Síntesis Ejecutiva (TLDR)
    const summaryData = backendFormats.tldr
      || backendFormats.summary 
      || backendFormats.sintesis 
      || activeSection?.sintesis
      || (globalStatus === 'processing' || globalStatus === 'pending' || globalStatus === 'loading' ? { status: globalStatus === 'pending' ? 'pending' : 'processing' } : null)
      || (globalStatus === 'error' ? { status: 'failed', errorMessage: 'No fue posible generar la Síntesis Ejecutiva.' } : null);
    summary.render(summaryData);
  },

  /**
   * Consulta GET /documents/{id}/formats al Backend y sincroniza el estado
   * @param {Object} doc - Documento activo
   * @param {boolean} isManualRetry - Indica si la petición fue provocada por el usuario
   */
  async fetchFormatsForCurrentDocument(doc, isManualRetry = false) {
    if (!doc?.id || this.isFetchingFormats) return;
    this.isFetchingFormats = true;
    this.updateHeaderButtonUI('loading');

    try {
      state.set({
        studyHub: {
          ...state.get().studyHub,
          formatsStatus: 'loading'
        }
      });

      const formatsResponse = await apiClient.getDocumentFormats(doc.id);
      const resolvedFormats = formatsResponse?.formats || formatsResponse;
      const globalStatus = formatsResponse?.status || (resolvedFormats ? 'ready' : 'empty');

      state.set({
        studyHub: {
          ...state.get().studyHub,
          formats: resolvedFormats,
          formatsStatus: globalStatus
        }
      });

      if (globalStatus === 'ready') {
        notifySuccess('Formatos Listos', 'Materiales de capacitación disponibles.');

        // Recuperar metadatos pedagógicos del documento si aún no están en memoria (PR #63)
        if (!doc.learning_metadata && doc.id && !doc.id.startsWith('mock_')) {
          apiClient.getDocumentById(doc.id).then(docDetail => {
            if (docDetail?.learning_metadata) {
              const s = state.get();
              if (s.currentDocument?.id === doc.id) {
                state.set({
                  currentDocument: {
                    ...s.currentDocument,
                    learning_metadata: docDetail.learning_metadata,
                    key_concepts: docDetail.learning_metadata.key_concepts || s.currentDocument.key_concepts,
                    prerequisites: docDetail.learning_metadata.prerequisites || s.currentDocument.prerequisites,
                    estimated_time_minutes: docDetail.learning_metadata.estimated_time_minutes ?? s.currentDocument.estimated_time_minutes,
                    summary: docDetail.summary || s.currentDocument.summary
                  }
                });
              }
            }
          }).catch(() => {});
        }
      } else if (globalStatus === 'processing') {
        this.startPolling(doc.id);
      } else if (globalStatus === 'partial') {
        notifyWarning('Generación Parcial', 'Uno de los formatos se completó, pero el otro presentó un fallo.');
      } else if (globalStatus === 'error') {
        notifyError('Fallo en Formatos', 'No fue posible generar los formatos pedagógicos.');
      }
    } catch (err) {
      console.warn('[StudyHub] Error al consultar formatos desde el backend:', err.message);
      state.set({
        studyHub: {
          ...state.get().studyHub,
          formatsStatus: 'error'
        }
      });

      const friendly = toFriendlyError(err);
      statusDialog.showError({
        status: friendly.status,
        code: friendly.code,
        message: friendly.message,
        details: [`Documento ID: ${doc.id}`, ...friendly.details],
        filename: doc.filename || doc.title
      });
      notifyError(friendly.title, friendly.message);
    } finally {
      this.isFetchingFormats = false;
      const currentGlobalStatus = state.get().studyHub?.formatsStatus || 'ready';
      this.updateHeaderButtonUI(currentGlobalStatus);
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
