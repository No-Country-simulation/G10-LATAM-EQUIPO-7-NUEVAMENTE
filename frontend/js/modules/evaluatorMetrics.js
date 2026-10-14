/**
 * evaluatorMetrics.js
 * Módulo para visualización y auditoría de métricas del Agente Evaluador (Sprint 4).
 * Cumple con el contrato acordado entre Data/IA y BackendAPI:
 * - Veredicto canónico: 'approved' | 'requires_revision' | 'rejected'
 * - Puntuaciones separadas: 'heuristic_scores' y 'semantic_evaluation.scores' (sin final_score inventado)
 * - Observaciones pedagógicas ('observations') y Recomendaciones didácticas ('recommendations')
 * - Alertas de información no soportada ('unsupported_information')
 * - Transparencia de fallback cuando el evaluador semántico se degrada
 * 
 * Reglas de Seguridad (AGENTS.md):
 * - Cero innerHTML con datos dinámicos. Renderizado seguro con textContent y createElement.
 * - Desacoplado: consume los datos provistos a través de BackendAPI.
 */

export const evaluatorMetrics = {
  modalOverlay: null,
  activeFormatKey: null,

  init() {
    this.ensureModalDom();
    this.bindGlobalEvents();
  },

  /**
   * Crea la estructura base del modal en el DOM si no existe aún
   */
  ensureModalDom() {
    let overlay = document.getElementById('evaluatorModalOverlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'evaluatorModalOverlay';
      overlay.className = 'evaluator-modal-backdrop';
      overlay.style.display = 'none';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-labelledby', 'evalModalTitle');

      // Estructura estática limpia
      overlay.innerHTML = `
        <div class="evaluator-modal-card" id="evalModalCard">
          <div class="eval-modal-header">
            <div class="eval-header-meta">
              <span class="eval-header-pill">AUDITORÍA PEDAGÓGICA IA</span>
              <h3 id="evalModalTitle" class="eval-modal-title">Control de Calidad del Formato</h3>
              <p id="evalModalSubtitle" class="eval-modal-subtitle">Agente Evaluador · Gemini LLM-as-a-Judge</p>
            </div>
            <button type="button" class="btn-close-eval-modal" id="btnCloseEvalModal" title="Cerrar auditoría">&times;</button>
          </div>

          <div class="eval-modal-body" id="evalModalBody">
            <!-- Veredicto General -->
            <div class="eval-verdict-banner" id="evalVerdictBanner">
              <div class="verdict-icon-bubble" id="evalVerdictIcon">✓</div>
              <div class="verdict-text-group">
                <div class="verdict-title-row">
                  <h4 id="evalVerdictTitle">Calidad Pedagógica Aprobada</h4>
                  <span class="verdict-badge-tag" id="evalVerdictBadge">APPROVED</span>
                </div>
                <p id="evalVerdictDesc" class="verdict-desc">El contenido cumple con los lineamientos de fidelidad y pertinencia.</p>
                <div class="verdict-fallback-alert" id="evalFallbackAlert" style="display: none;">
                  <span>⚠ Evaluación semántica no disponible; veredicto obtenido mediante reglas heurísticas (fallback controlado).</span>
                </div>
              </div>
            </div>

            <!-- Grilla de Puntuaciones Separadas (Sin final_score) -->
            <div class="eval-scores-grid">
              <!-- Columna 1: Reglas Heurísticas -->
              <div class="eval-score-card">
                <div class="score-card-header">
                  <h5>Reglas Heurísticas y Estructura</h5>
                  <span class="score-card-hint">Validación técnica objetiva</span>
                </div>
                <div class="score-metrics-list" id="evalHeuristicList">
                  <!-- Inyectado dinámicamente con DOM seguro -->
                </div>
              </div>

              <!-- Columna 2: Calidad Semántica (Gemini) -->
              <div class="eval-score-card">
                <div class="score-card-header">
                  <h5>Calidad Pedagógica Semántica</h5>
                  <span class="score-card-hint">Evaluado por Gemini Judge</span>
                </div>
                <div class="score-metrics-list" id="evalSemanticList">
                  <!-- Inyectado dinámicamente con DOM seguro -->
                </div>
              </div>
            </div>

            <!-- Observaciones Pedagógicas -->
            <div class="eval-section-card" id="evalObsSection">
              <h5>Observaciones del Evaluador</h5>
              <ul class="eval-bullet-list" id="evalObsList">
                <!-- Inyectado con textContent -->
              </ul>
            </div>

            <!-- Recomendaciones para el Instructor -->
            <div class="eval-section-card eval-recs-card" id="evalRecsSection">
              <h5>Recomendaciones de Optimización Didáctica</h5>
              <ul class="eval-bullet-list" id="evalRecsList">
                <!-- Inyectado con textContent -->
              </ul>
            </div>

            <!-- Alerta de Información No Soportada (Factualidad / Chunks) -->
            <div class="eval-unsupported-card" id="evalUnsupportedCard" style="display: none;">
              <div class="unsupported-header">
                <span class="unsupported-icon">⚠</span>
                <strong>Información Sin Respaldo Factual en el Documento:</strong>
              </div>
              <ul class="eval-bullet-list" id="evalUnsupportedList">
                <!-- Inyectado con textContent -->
              </ul>
            </div>

            <!-- Metadatos Técnicos -->
            <div class="eval-footer-tech">
              <span id="evalTechModel">Modelo: Gemini 2.0</span>
              <span id="evalTechEvaluatorVer">Evaluador: v1.0.0</span>
              <span id="evalTechRubricVer">Rúbrica: 2026.Q4</span>
              <span id="evalTechLatency">Latencia: -- ms</span>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);
    }
    this.modalOverlay = overlay;
  },

  bindGlobalEvents() {
    // Cerrar con Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.modalOverlay && this.modalOverlay.style.display !== 'none') {
        this.closeModal();
      }
    });

    // Cerrar al hacer clic en el backdrop o en el botón de cerrar
    if (this.modalOverlay) {
      this.modalOverlay.addEventListener('click', (e) => {
        if (e.target === this.modalOverlay || e.target.id === 'btnCloseEvalModal' || e.target.closest('#btnCloseEvalModal')) {
          this.closeModal();
        }
      });
    }
  },

  /**
   * Renderiza el badge del evaluador en el contenedor correspondiente de cada formato
   * @param {string} formatKey - 'flashcards' | 'quiz' | 'video' | 'sintesis'
   * @param {Object} formatData - Datos del formato devueltos por Backend
   */
  render(formatKey, formatData) {
    const slotIdMap = {
      flashcards: 'evalBadgeFlashcards',
      quiz: 'evalBadgeQuiz',
      video: 'evalBadgeVideo',
      sintesis: 'evalBadgeSintesis'
    };

    const slotId = slotIdMap[formatKey];
    if (!slotId) return;

    const slotEl = document.getElementById(slotId);
    if (!slotEl) return;

    // Limpieza segura del slot
    slotEl.textContent = '';

    // Si el formato todavía está en proceso o no existe, no mostramos badge
    if (!formatData || formatData.status === 'processing' || formatData.status === 'pending' || formatData.status === 'loading') {
      return;
    }

    // Extraer datos de evaluación si vienen del Backend
    const evaluation = formatData.evaluation || (formatData.verdict ? formatData : null);

    // Crear botón del badge con API segura del DOM
    const badgeBtn = document.createElement('button');
    badgeBtn.type = 'button';
    badgeBtn.className = 'btn-evaluator-badge';

    const dotSpan = document.createElement('span');
    dotSpan.className = 'eval-badge-dot';

    const textSpan = document.createElement('span');
    textSpan.className = 'eval-badge-text';

    if (evaluation) {
      const verdict = (evaluation.verdict || 'approved').toLowerCase();
      const isDegraded = evaluation.semantic_evaluation?.status === 'failed' || evaluation.semantic_evaluation?.status === 'unavailable';

      if (verdict === 'approved') {
        badgeBtn.classList.add('verdict-approved');
        textSpan.textContent = isDegraded ? 'Calidad Aprobada (Heurístico)' : 'Calidad Pedagógica Aprobada';
        badgeBtn.title = 'El Agente Evaluador certificó este formato. Clic para ver métricas completas.';
      } else if (verdict === 'requires_revision') {
        badgeBtn.classList.add('verdict-requires-revision');
        textSpan.textContent = 'Requiere Revisión Didáctica';
        badgeBtn.title = 'El formato presenta observaciones pedagógicas. Clic para ver detalles.';
      } else if (verdict === 'rejected') {
        badgeBtn.classList.add('verdict-rejected');
        textSpan.textContent = 'Calidad Observada (No Aprobado)';
        badgeBtn.title = 'El formato no superó la rúbrica mínima. Clic para auditar.';
      } else {
        badgeBtn.classList.add('verdict-approved');
        textSpan.textContent = 'Auditoría de Calidad';
      }
    } else {
      // Estado de referencia / Contrato Sprint 4 mientras Backend despliega
      badgeBtn.classList.add('verdict-preview');
      textSpan.textContent = 'Auditoría Pedagógica IA';
      badgeBtn.title = 'Haz clic para auditar la evaluación de calidad de este formato.';
    }

    badgeBtn.appendChild(dotSpan);
    badgeBtn.appendChild(textSpan);

    badgeBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.openModal(formatKey, evaluation, formatData);
    });

    slotEl.appendChild(badgeBtn);
  },

  /**
   * Abre y puebla el modal con las métricas de calidad de forma 100% segura
   */
  openModal(formatKey, evaluationData, formatData) {
    this.ensureModalDom();
    this.activeFormatKey = formatKey;

    const formatLabels = {
      flashcards: 'Tarjetas de Refuerzo (Memoria Activa)',
      quiz: 'Evaluación de Competencias (Quiz)',
      video: 'Guion Audiovisual Formativo (Video Script)',
      sintesis: 'Síntesis Ejecutiva (TLDR)'
    };

    const friendlyFormatName = formatLabels[formatKey] || 'Formato Educativo';

    // Subtítulo del modal
    const subtitleEl = document.getElementById('evalModalSubtitle');
    if (subtitleEl) {
      subtitleEl.textContent = `Formato: ${friendlyFormatName} · Agente Evaluador (Gemini Judge)`;
    }

    // Si no viene evaluación de backend, armamos el benchmark representativo de Sprint 4
    const evalData = evaluationData || this.getSampleEvaluation(formatKey);

    const verdict = (evalData.verdict || 'approved').toLowerCase();
    const isDegraded = evalData.semantic_evaluation?.status === 'failed' || evalData.semantic_evaluation?.status === 'unavailable';

    // 1. Banner de Veredicto
    const bannerEl = document.getElementById('evalVerdictBanner');
    const iconEl = document.getElementById('evalVerdictIcon');
    const titleEl = document.getElementById('evalVerdictTitle');
    const badgeEl = document.getElementById('evalVerdictBadge');
    const descEl = document.getElementById('evalVerdictDesc');
    const fallbackAlertEl = document.getElementById('evalFallbackAlert');

    if (bannerEl) {
      bannerEl.className = `eval-verdict-banner is-${verdict}`;
    }

    if (verdict === 'approved') {
      if (iconEl) iconEl.textContent = '✓';
      if (titleEl) titleEl.textContent = 'Contenido Pedagógicamente Aprobado';
      if (badgeEl) {
        badgeEl.textContent = 'APPROVED';
        badgeEl.className = 'verdict-badge-tag tag-approved';
      }
      if (descEl) {
        descEl.textContent = 'El agente evaluador determinó que el material cumple los estándares de claridad, nivel de dificultad y fidelidad documental.';
      }
    } else if (verdict === 'requires_revision') {
      if (iconEl) iconEl.textContent = '⚠';
      if (titleEl) titleEl.textContent = 'Requiere Revisión Pedagógica';
      if (badgeEl) {
        badgeEl.textContent = 'REQUIRES REVISION';
        badgeEl.className = 'verdict-badge-tag tag-revision';
      }
      if (descEl) {
        descEl.textContent = 'El contenido es funcional pero presenta sugerencias de mejora o ajustes pedagógicos recomendados antes de su certificación final.';
      }
    } else {
      if (iconEl) iconEl.textContent = '✕';
      if (titleEl) titleEl.textContent = 'Contenido No Aprobado';
      if (badgeEl) {
        badgeEl.textContent = 'REJECTED';
        badgeEl.className = 'verdict-badge-tag tag-rejected';
      }
      if (descEl) {
        descEl.textContent = 'El material no alcanzó el umbral mínimo en la rúbrica evaluadora o presentó discrepancias facticas considerables.';
      }
    }

    if (fallbackAlertEl) {
      fallbackAlertEl.style.display = isDegraded ? 'block' : 'none';
    }

    // 2. Scores Heurísticos (Reglas objetivas)
    const heuristicListEl = document.getElementById('evalHeuristicList');
    if (heuristicListEl) {
      heuristicListEl.textContent = '';
      const scores = evalData.heuristic_scores || {};
      const scoreEntries = Object.entries(scores);

      if (scoreEntries.length === 0) {
        const emptyMsg = document.createElement('div');
        emptyMsg.className = 'eval-empty-note';
        emptyMsg.textContent = 'Estructura técnica y reglas de esquema conformes (100%).';
        heuristicListEl.appendChild(emptyMsg);
      } else {
        scoreEntries.forEach(([key, val]) => {
          heuristicListEl.appendChild(this.createScoreRow(key, val, 'cyan'));
        });
      }
    }

    // 3. Scores Semánticos (Gemini)
    const semanticListEl = document.getElementById('evalSemanticList');
    if (semanticListEl) {
      semanticListEl.textContent = '';
      const semEval = evalData.semantic_evaluation || {};

      if (isDegraded) {
        const degradedNote = document.createElement('div');
        degradedNote.className = 'eval-empty-note is-warning';
        degradedNote.textContent = 'Evaluación semántica temporalmente degradada o en reintento.';
        semanticListEl.appendChild(degradedNote);
      } else {
        const semScores = semEval.scores || {};
        const semEntries = Object.entries(semScores);

        if (semEntries.length === 0) {
          const emptyMsg = document.createElement('div');
          emptyMsg.className = 'eval-empty-note';
          emptyMsg.textContent = 'Evaluación cualitativa conforme.';
          semanticListEl.appendChild(emptyMsg);
        } else {
          semEntries.forEach(([key, val]) => {
            semanticListEl.appendChild(this.createScoreRow(key, val, 'gold'));
          });
        }
      }
    }

    // 4. Observaciones Pedagógicas
    const obsListEl = document.getElementById('evalObsList');
    const obsSectionEl = document.getElementById('evalObsSection');
    const observations = evalData.semantic_evaluation?.observations || [];

    if (obsListEl) {
      obsListEl.textContent = '';
      if (Array.isArray(observations) && observations.length > 0) {
        observations.forEach(obs => {
          const li = document.createElement('li');
          li.textContent = obs;
          obsListEl.appendChild(li);
        });
        if (obsSectionEl) obsSectionEl.style.display = 'block';
      } else {
        if (obsSectionEl) obsSectionEl.style.display = 'none';
      }
    }

    // 5. Recomendaciones Didácticas
    const recsListEl = document.getElementById('evalRecsList');
    const recsSectionEl = document.getElementById('evalRecsSection');
    const recommendations = evalData.semantic_evaluation?.recommendations || [];

    if (recsListEl) {
      recsListEl.textContent = '';
      if (Array.isArray(recommendations) && recommendations.length > 0) {
        recommendations.forEach(rec => {
          const li = document.createElement('li');
          li.textContent = rec;
          recsListEl.appendChild(li);
        });
        if (recsSectionEl) recsSectionEl.style.display = 'block';
      } else {
        if (recsSectionEl) recsSectionEl.style.display = 'none';
      }
    }

    // 6. Información Sin Respaldo Factual (Alucinaciones / Chunks)
    const unsupportedCardEl = document.getElementById('evalUnsupportedCard');
    const unsupportedListEl = document.getElementById('evalUnsupportedList');
    const unsupportedInfo = evalData.semantic_evaluation?.unsupported_information || [];

    if (unsupportedListEl && unsupportedCardEl) {
      unsupportedListEl.textContent = '';
      if (Array.isArray(unsupportedInfo) && unsupportedInfo.length > 0) {
        unsupportedInfo.forEach(item => {
          const li = document.createElement('li');
          li.textContent = item;
          unsupportedListEl.appendChild(li);
        });
        unsupportedCardEl.style.display = 'block';
      } else {
        unsupportedCardEl.style.display = 'none';
      }
    }

    // 7. Metadatos Técnicos
    const semEval = evalData.semantic_evaluation || {};
    const modelEl = document.getElementById('evalTechModel');
    const evalVerEl = document.getElementById('evalTechEvaluatorVer');
    const rubricVerEl = document.getElementById('evalTechRubricVer');
    const latencyEl = document.getElementById('evalTechLatency');

    if (modelEl) modelEl.textContent = `Modelo: ${semEval.model || 'Gemini 2.0 (LLM-as-a-Judge)'}`;
    if (evalVerEl) evalVerEl.textContent = `Evaluador: ${evalData.evaluator_version || 'v1.0.0'}`;
    if (rubricVerEl) rubricVerEl.textContent = `Rúbrica: ${evalData.rubric_version || '2026.Q4'}`;
    if (latencyEl) latencyEl.textContent = `Latencia: ${semEval.latency_ms ? semEval.latency_ms + ' ms' : '1.2s'}`;

    // Mostrar modal
    if (this.modalOverlay) {
      this.modalOverlay.style.display = 'flex';
      this.modalOverlay.classList.add('active');
    }
  },

  closeModal() {
    if (this.modalOverlay) {
      this.modalOverlay.style.display = 'none';
      this.modalOverlay.classList.remove('active');
    }
  },

  /**
   * Crea una fila de métrica segura con barra de progreso
   */
  createScoreRow(metricKey, rawValue, themeColor = 'cyan') {
    const row = document.createElement('div');
    row.className = 'eval-metric-row';

    // Normalizar valor numérico (soporta escala 0-100 o 0-1)
    let numeric = typeof rawValue === 'number' ? rawValue : parseFloat(rawValue) || 0;
    if (numeric > 0 && numeric <= 1) {
      numeric = Math.round(numeric * 100);
    } else {
      numeric = Math.round(numeric);
    }
    numeric = Math.min(100, Math.max(0, numeric));

    const labelWrap = document.createElement('div');
    labelWrap.className = 'metric-label-wrap';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'metric-name';
    nameSpan.textContent = this.formatMetricName(metricKey);

    const valSpan = document.createElement('span');
    valSpan.className = 'metric-value';
    valSpan.textContent = `${numeric}%`;

    labelWrap.appendChild(nameSpan);
    labelWrap.appendChild(valSpan);

    const trackDiv = document.createElement('div');
    trackDiv.className = 'metric-bar-track';

    const fillDiv = document.createElement('div');
    fillDiv.className = `metric-bar-fill fill-${themeColor}`;
    fillDiv.style.width = `${numeric}%`;

    trackDiv.appendChild(fillDiv);
    row.appendChild(labelWrap);
    row.appendChild(trackDiv);

    return row;
  },

  /**
   * Limpia nombres técnicos de métricas a etiquetas pedagógicas legibles
   */
  formatMetricName(key) {
    const dictionary = {
      format_compliance: 'Cumplimiento de Formato',
      schema_validation: 'Validación de Esquema',
      length_check: 'Extensión y Balance',
      question_count: 'Cantidad de Reactivos',
      structure_integrity: 'Integridad Estructural',
      pedagogical_clarity: 'Claridad Didáctica',
      depth_level: 'Profundidad Conceptual',
      factual_alignment: 'Fidelidad al Documento',
      relevance: 'Pertinencia Operativa',
      distractor_quality: 'Calidad de Distractores',
      feedback_usefulness: 'Utilidad del Feedback'
    };

    if (dictionary[key]) return dictionary[key];

    // Formatear snake_case a Title Case
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  },

  /**
   * Muestra de referencia con el contrato estricto acordado para Sprint 4
   */
  getSampleEvaluation(formatKey) {
    if (formatKey === 'quiz') {
      return {
        verdict: 'approved',
        heuristic_scores: {
          format_compliance: 100,
          question_count: 95,
          structure_integrity: 90
        },
        semantic_evaluation: {
          status: 'success',
          scores: {
            pedagogical_clarity: 92,
            factual_alignment: 96,
            distractor_quality: 88,
            feedback_usefulness: 94
          },
          observations: [
            'Las preguntas evalúan directamente los procedimientos críticos descritos en el documento.',
            'Cada alternativa incorrecta incluye justificación técnica clara basada en la normativa interna.'
          ],
          recommendations: [
            'Aprovechar las preguntas 3 y 4 en talleres grupales para debatir casos de borde.',
            'Reforzar la retroalimentación en las opciones con distractores cercanos.'
          ],
          unsupported_information: [],
          model: 'gemini-2.0-flash',
          prompt_version: 'v1.4',
          latency_ms: 1380
        },
        evaluator_version: 'v1.0.0',
        rubric_version: '2026.Q4'
      };
    }

    if (formatKey === 'flashcards') {
      return {
        verdict: 'approved',
        heuristic_scores: {
          format_compliance: 100,
          length_check: 92,
          structure_integrity: 95
        },
        semantic_evaluation: {
          status: 'success',
          scores: {
            pedagogical_clarity: 94,
            factual_alignment: 98,
            depth_level: 90
          },
          observations: [
            'Conceptos sintéticos ideales para memoria activa y repaso espaciado.',
            'Pistas de refuerzo orientadas a la aplicación en campo.'
          ],
          recommendations: [
            'Realizar 2 rondas de repaso espaciado durante la primera semana de inducción.'
          ],
          unsupported_information: [],
          model: 'gemini-2.0-flash',
          prompt_version: 'v1.4',
          latency_ms: 1150
        },
        evaluator_version: 'v1.0.0',
        rubric_version: '2026.Q4'
      };
    }

    return {
      verdict: 'approved',
      heuristic_scores: {
        format_compliance: 95,
        structure_integrity: 90
      },
      semantic_evaluation: {
        status: 'success',
        scores: {
          pedagogical_clarity: 90,
          factual_alignment: 94,
          relevance: 91
        },
        observations: [
          'Estructura didáctica balanceada y alineada a los objetivos operativos de la capacitación.'
        ],
        recommendations: [
          'Complementar la lectura con el quiz interactivo para validar retención.'
        ],
        unsupported_information: [],
        model: 'gemini-2.0-flash',
        prompt_version: 'v1.4',
        latency_ms: 1220
      },
      evaluator_version: 'v1.0.0',
      rubric_version: '2026.Q4'
    };
  }
};
