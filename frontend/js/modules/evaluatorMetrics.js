/**
 * evaluatorMetrics.js
 * Módulo para visualización y auditoría de métricas del Agente Evaluador V2.
 * Cumple con el contrato acordado de consenso entre Data/IA, BackendAPI y Frontend:
 * - Veredicto canónico: 'approved' | 'requires_revision' | 'rejected' | null (sin veredicto / en evaluación)
 * - Puntuaciones separadas: 'heuristic_scores' y 'semantic_evaluation.scores' en escala 1.0 a 5.0 (sin final_score inventado)
 * - Cuatro dimensiones canónicas: 'relevance', 'coherence', 'didactic_adaptation', 'content_support'
 * - Observaciones pedagógicas estructuradas ('observations': [{ dimension, severity, message, item_id }])
 * - Recomendaciones didácticas estructuradas ('recommendations': [{ dimension, message, item_id }])
 * - Información no respaldada ('unsupported_information': [{ claim, reason, item_id, related_chunk_ids }])
 * - Manejo robusto de estados semánticos: 'success', 'unavailable' (error: not_configured), 'failed' (error: timeout u otro)
 * - Soporte de ciclo de generación/corrección: visualización y navegación de intentos ('evaluations' array)
 * 
 * Reglas de Seguridad (AGENTS.md):
 * - Cero innerHTML con datos dinámicos. Renderizado seguro con textContent y createElement.
 * - Desacoplado: consume los datos provistos a través de BackendAPI.
 */

export const evaluatorMetrics = {
  modalOverlay: null,
  activeFormatKey: null,
  activeAttemptIndex: 0,
  currentEvaluationsList: [],
  currentFormatData: null,

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

      // Estructura estática limpia (sin datos dinámicos)
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
            <!-- Barra de Selección de Intentos del Ciclo (V2) -->
            <div class="eval-cycle-bar" id="evalCycleBar" style="display: none;">
              <!-- Botones de ciclo inyectados con DOM seguro -->
            </div>

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
                  <span id="evalFallbackAlertText">⚠ Evaluación semántica no disponible; veredicto obtenido mediante reglas heurísticas (fallback controlado).</span>
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
              <span id="evalTechModel">Modelo: --</span>
              <span id="evalTechEvaluatorVer">Evaluador: --</span>
              <span id="evalTechRubricVer">Rúbrica: --</span>
              <span id="evalTechLatency">Latencia: --</span>
              <span id="evalTechFormatId">Formato: --</span>
              <span id="evalTechEvalId">ID: --</span>
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

    // Extraer datos de evaluación según contrato V2
    const evaluation = formatData.evaluation 
      || (Array.isArray(formatData.evaluations) && formatData.evaluations.length > 0 ? formatData.evaluations[0] : null)
      || (formatData.verdict ? formatData : null);

    // Crear botón del badge con API segura del DOM
    const badgeBtn = document.createElement('button');
    badgeBtn.type = 'button';
    badgeBtn.className = 'btn-evaluator-badge';

    const dotSpan = document.createElement('span');
    dotSpan.className = 'eval-badge-dot';

    const textSpan = document.createElement('span');
    textSpan.className = 'eval-badge-text';

    if (evaluation) {
      const verdict = evaluation.verdict ? evaluation.verdict.toLowerCase() : null;
      const semStatus = evaluation.semantic_evaluation?.status;
      const isDegraded = semStatus === 'failed' || semStatus === 'unavailable';

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
        // verdict === null
        badgeBtn.classList.add('verdict-preview');
        textSpan.textContent = semStatus === 'failed' ? 'Evaluación Incompleta' : 'En Evaluación Pedagógica';
        badgeBtn.title = 'Evaluación técnica registrada sin veredicto definitivo. Clic para inspeccionar.';
      }
    } else {
      // Estado informativo cuando evaluation es null (ej. tldr en phase evaluating)
      badgeBtn.classList.add('verdict-preview');
      textSpan.textContent = 'En Evaluación Pedagógica';
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
    this.currentFormatData = formatData;

    const formatLabels = {
      flashcards: 'Tarjetas de Refuerzo (Memoria Activa)',
      quiz: 'Evaluación de Competencias (Quiz)',
      video: 'Guion Audiovisual Formativo (Video Script)',
      video_script: 'Guion Audiovisual Formativo (Video Script)',
      sintesis: 'Síntesis Ejecutiva (TLDR)',
      tldr: 'Síntesis Ejecutiva (TLDR)'
    };

    const friendlyFormatName = formatLabels[formatKey] || 'Formato Educativo';

    // Subtítulo del modal
    const subtitleEl = document.getElementById('evalModalSubtitle');
    if (subtitleEl) {
      subtitleEl.textContent = `Formato: ${friendlyFormatName} · Agente Evaluador (Gemini Judge)`;
    }

    // Resolver lista de evaluaciones del ciclo (V2)
    let evaluationsList = [];
    if (formatData?.evaluations && Array.isArray(formatData.evaluations) && formatData.evaluations.length > 0) {
      evaluationsList = formatData.evaluations;
    } else if (evaluationData) {
      evaluationsList = [evaluationData];
    } else if (formatData) {
      // Formato real devuelto por Backend sin evaluación emitida (evaluation: null, evaluations: [])
      evaluationsList = [];
    } else {
      // Benchmark representativo solo si se invoca la vista en seco sin formatData
      evaluationsList = this.getSampleEvaluations(formatKey);
    }

    this.currentEvaluationsList = evaluationsList;
    this.activeAttemptIndex = 0;

    // Renderizar selector de intentos del ciclo si hay más de una evaluación
    this.renderCycleSelector();

    // Renderizar el intento seleccionado
    const selectedEval = evaluationsList[this.activeAttemptIndex] || null;
    this.renderAttempt(selectedEval, formatKey, formatData);

    // Mostrar modal
    if (this.modalOverlay) {
      this.modalOverlay.style.display = 'flex';
      this.modalOverlay.classList.add('active');
    }
  },

  /**
   * Renderiza el selector de ciclos/intentos de evaluación si existen múltiples intentos
   */
  renderCycleSelector() {
    const cycleBar = document.getElementById('evalCycleBar');
    if (!cycleBar) return;

    cycleBar.textContent = ''; // Limpieza segura

    const list = this.currentEvaluationsList || [];
    if (list.length <= 1) {
      cycleBar.style.display = 'none';
      return;
    }

    cycleBar.style.display = 'flex';

    const labelSpan = document.createElement('span');
    labelSpan.className = 'eval-cycle-label';
    labelSpan.textContent = 'Historial del Ciclo:';
    cycleBar.appendChild(labelSpan);

    const totalAttempts = list.length;
    list.forEach((evalItem, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `eval-cycle-btn${index === this.activeAttemptIndex ? ' is-active' : ''}`;

      const attemptNumber = totalAttempts - index;
      const isLatest = index === 0;
      const isInitial = index === totalAttempts - 1;

      let suffix = '';
      if (isLatest && totalAttempts > 1) {
        suffix = ' (Actual - Corregido)';
      } else if (isInitial) {
        suffix = ' (Inicial)';
      }

      btn.textContent = `Intento ${attemptNumber}${suffix}`;

      // Veredicto en miniatura
      const v = (evalItem?.verdict || 'none').toLowerCase();
      const dot = document.createElement('span');
      dot.className = `eval-badge-dot`;
      dot.style.marginLeft = '0.35rem';
      if (v === 'approved') {
        dot.style.background = '#10b981';
      } else if (v === 'requires_revision') {
        dot.style.background = '#f59e0b';
      } else if (v === 'rejected') {
        dot.style.background = '#ef4444';
      } else {
        dot.style.background = '#94a3b8';
      }
      btn.appendChild(dot);

      btn.addEventListener('click', (e) => {
        e.preventDefault();
        this.activeAttemptIndex = index;
        this.renderCycleSelector();
        this.renderAttempt(list[index], this.activeFormatKey, this.currentFormatData);
      });

      cycleBar.appendChild(btn);
    });
  },

  /**
   * Puebla los datos de un intento específico de evaluación en el modal
   */
  renderAttempt(evalData, formatKey, formatData) {
    // Si no hay evaluación disponible (ej. tldr en phase evaluating)
    if (!evalData) {
      this.renderEmptyAttempt(formatData);
      return;
    }

    const verdict = evalData.verdict ? evalData.verdict.toLowerCase() : null;
    const semEval = evalData.semantic_evaluation || {};
    const semStatus = (semEval.status || '').toLowerCase();
    const isDegraded = semStatus === 'failed' || semStatus === 'unavailable';

    // 1. Banner de Veredicto
    const bannerEl = document.getElementById('evalVerdictBanner');
    const iconEl = document.getElementById('evalVerdictIcon');
    const titleEl = document.getElementById('evalVerdictTitle');
    const badgeEl = document.getElementById('evalVerdictBadge');
    const descEl = document.getElementById('evalVerdictDesc');
    const fallbackAlertEl = document.getElementById('evalFallbackAlert');
    const fallbackTextEl = document.getElementById('evalFallbackAlertText');

    if (bannerEl) {
      bannerEl.className = `eval-verdict-banner is-${verdict || 'neutral'}`;
    }

    if (verdict === 'approved') {
      if (iconEl) iconEl.textContent = '✓';
      if (titleEl) titleEl.textContent = 'Contenido Pedagógicamente Aprobado';
      if (badgeEl) {
        badgeEl.textContent = 'APPROVED';
        badgeEl.className = 'verdict-badge-tag tag-approved';
      }
      if (descEl) {
        descEl.textContent = 'El agente evaluador determinó que el material cumple los estándares de fidelidad y pertinencia pedagógica.';
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
    } else if (verdict === 'rejected') {
      if (iconEl) iconEl.textContent = '✕';
      if (titleEl) titleEl.textContent = 'Contenido No Aprobado';
      if (badgeEl) {
        badgeEl.textContent = 'REJECTED';
        badgeEl.className = 'verdict-badge-tag tag-rejected';
      }
      if (descEl) {
        descEl.textContent = 'El material no alcanzó el umbral mínimo en la rúbrica evaluadora o presentó discrepancias fácticas considerables.';
      }
    } else {
      // verdict === null
      if (iconEl) iconEl.textContent = 'ℹ';
      if (titleEl) titleEl.textContent = 'Evaluación Sin Veredicto Pedagógico';
      if (badgeEl) {
        badgeEl.textContent = 'SIN VEREDICTO';
        badgeEl.className = 'verdict-badge-tag tag-neutral';
      }
      if (descEl) {
        descEl.textContent = 'No se ha emitido una decisión pedagógica automática para este intento de generación.';
      }
    }

    // Mensaje de estado degradado / fallback
    if (fallbackAlertEl && fallbackTextEl) {
      if (semStatus === 'unavailable') {
        fallbackAlertEl.style.display = 'block';
        fallbackTextEl.textContent = `ℹ Evaluador semántico no configurado (${semEval.error_code || 'not_configured'}). Validación fundamentada en reglas heurísticas.`;
      } else if (semStatus === 'failed') {
        fallbackAlertEl.style.display = 'block';
        fallbackTextEl.textContent = `⚠ Evaluación semántica no disponible (error: ${semEval.error_code || 'interrupción técnica'}). Conservando evaluación heurística si existe.`;
      } else {
        fallbackAlertEl.style.display = 'none';
      }
    }

    // 2. Scores Heurísticos (Escala 1.0 - 5.0)
    const heuristicListEl = document.getElementById('evalHeuristicList');
    if (heuristicListEl) {
      heuristicListEl.textContent = '';
      const scores = evalData.heuristic_scores;

      if (!scores || Object.keys(scores).length === 0) {
        const emptyMsg = document.createElement('div');
        emptyMsg.className = 'eval-empty-note';
        emptyMsg.textContent = 'Sin puntuaciones heurísticas registradas en este intento.';
        heuristicListEl.appendChild(emptyMsg);
      } else {
        Object.entries(scores).forEach(([key, val]) => {
          if (val !== null && val !== undefined) {
            const row = this.createScoreRow(key, val, 'cyan');
            if (row) heuristicListEl.appendChild(row);
          }
        });
      }
    }

    // 3. Scores Semánticos (Escala 1.0 - 5.0)
    const semanticListEl = document.getElementById('evalSemanticList');
    if (semanticListEl) {
      semanticListEl.textContent = '';

      if (semStatus === 'unavailable') {
        const note = document.createElement('div');
        note.className = 'eval-empty-note is-warning';
        note.textContent = 'Evaluador semántico no configurado (scores no disponibles).';
        semanticListEl.appendChild(note);
      } else if (semStatus === 'failed') {
        const note = document.createElement('div');
        note.className = 'eval-empty-note is-warning';
        note.textContent = `Evaluación semántica interrumpida (${semEval.error_code || 'timeout'}).`;
        semanticListEl.appendChild(note);
      } else {
        const semScores = semEval.scores;
        if (!semScores || Object.keys(semScores).length === 0) {
          const emptyMsg = document.createElement('div');
          emptyMsg.className = 'eval-empty-note';
          emptyMsg.textContent = 'Sin puntuaciones semánticas registradas.';
          semanticListEl.appendChild(emptyMsg);
        } else {
          Object.entries(semScores).forEach(([key, val]) => {
            if (val !== null && val !== undefined) {
              const row = this.createScoreRow(key, val, 'gold');
              if (row) semanticListEl.appendChild(row);
            }
          });
        }
      }
    }

    // 4. Observaciones Pedagógicas (Estructuradas V2)
    const obsListEl = document.getElementById('evalObsList');
    const obsSectionEl = document.getElementById('evalObsSection');
    const observations = semEval.observations || [];

    if (obsListEl) {
      obsListEl.textContent = '';
      if (Array.isArray(observations) && observations.length > 0) {
        observations.forEach(obs => {
          const li = document.createElement('li');
          li.className = 'eval-obs-item';

          if (typeof obs === 'object' && obs !== null) {
            const metaRow = document.createElement('div');
            metaRow.className = 'eval-obs-meta';

            if (obs.severity) {
              const sevTag = document.createElement('span');
              sevTag.className = `eval-pill eval-pill-${obs.severity.toLowerCase()}`;
              sevTag.textContent = obs.severity.toUpperCase();
              metaRow.appendChild(sevTag);
            }

            if (obs.dimension) {
              const dimTag = document.createElement('span');
              dimTag.className = 'eval-pill eval-pill-dimension';
              dimTag.textContent = this.formatMetricName(obs.dimension);
              metaRow.appendChild(dimTag);
            }

            if (obs.item_id) {
              const itemTag = document.createElement('span');
              itemTag.className = 'eval-pill eval-pill-itemid';
              itemTag.textContent = `Reactivo: ${obs.item_id}`;
              metaRow.appendChild(itemTag);
            }

            const msgP = document.createElement('p');
            msgP.className = 'eval-obs-msg';
            msgP.textContent = obs.message || '';

            if (metaRow.children.length > 0) {
              li.appendChild(metaRow);
            }
            li.appendChild(msgP);
          } else {
            li.textContent = String(obs);
          }

          obsListEl.appendChild(li);
        });
        if (obsSectionEl) obsSectionEl.style.display = 'block';
      } else {
        if (obsSectionEl) obsSectionEl.style.display = 'none';
      }
    }

    // 5. Recomendaciones Didácticas (Estructuradas V2)
    const recsListEl = document.getElementById('evalRecsList');
    const recsSectionEl = document.getElementById('evalRecsSection');
    const recommendations = semEval.recommendations || [];

    if (recsListEl) {
      recsListEl.textContent = '';
      if (Array.isArray(recommendations) && recommendations.length > 0) {
        recommendations.forEach(rec => {
          const li = document.createElement('li');
          li.className = 'eval-rec-item';

          if (typeof rec === 'object' && rec !== null) {
            const metaRow = document.createElement('div');
            metaRow.className = 'eval-rec-meta';

            if (rec.dimension) {
              const dimTag = document.createElement('span');
              dimTag.className = 'eval-pill eval-pill-dimension';
              dimTag.textContent = this.formatMetricName(rec.dimension);
              metaRow.appendChild(dimTag);
            }

            if (rec.item_id) {
              const itemTag = document.createElement('span');
              itemTag.className = 'eval-pill eval-pill-itemid';
              itemTag.textContent = `Reactivo: ${rec.item_id}`;
              metaRow.appendChild(itemTag);
            }

            const msgP = document.createElement('p');
            msgP.className = 'eval-rec-msg';
            msgP.textContent = rec.message || '';

            if (metaRow.children.length > 0) {
              li.appendChild(metaRow);
            }
            li.appendChild(msgP);
          } else {
            li.textContent = String(rec);
          }

          recsListEl.appendChild(li);
        });
        if (recsSectionEl) recsSectionEl.style.display = 'block';
      } else {
        if (recsSectionEl) recsSectionEl.style.display = 'none';
      }
    }

    // 6. Información Sin Respaldo Factual (Factualidad / Chunks)
    const unsupportedCardEl = document.getElementById('evalUnsupportedCard');
    const unsupportedListEl = document.getElementById('evalUnsupportedList');
    const unsupportedInfo = semEval.unsupported_information || [];

    if (unsupportedListEl && unsupportedCardEl) {
      unsupportedListEl.textContent = '';
      if (Array.isArray(unsupportedInfo) && unsupportedInfo.length > 0) {
        unsupportedInfo.forEach(item => {
          const li = document.createElement('li');
          li.className = 'eval-unsupported-item';

          if (typeof item === 'object' && item !== null) {
            const claimDiv = document.createElement('div');
            claimDiv.className = 'unsupported-claim-row';
            const claimLabel = document.createElement('strong');
            claimLabel.textContent = 'Afirmación:';
            const claimText = document.createElement('span');
            claimText.textContent = item.claim || '';
            claimDiv.appendChild(claimLabel);
            claimDiv.appendChild(claimText);
            li.appendChild(claimDiv);

            if (item.reason) {
              const reasonDiv = document.createElement('div');
              reasonDiv.className = 'unsupported-reason-row';
              const reasonLabel = document.createElement('strong');
              reasonLabel.textContent = 'Motivo:';
              const reasonText = document.createElement('span');
              reasonText.textContent = item.reason;
              reasonDiv.appendChild(reasonLabel);
              reasonDiv.appendChild(reasonText);
              li.appendChild(reasonDiv);
            }

            if (item.item_id || (Array.isArray(item.related_chunk_ids) && item.related_chunk_ids.length > 0)) {
              const metaDiv = document.createElement('div');
              metaDiv.className = 'unsupported-meta-row';

              if (item.item_id) {
                const itemSpan = document.createElement('span');
                itemSpan.className = 'eval-pill eval-pill-itemid';
                itemSpan.textContent = `Reactivo: ${item.item_id}`;
                metaDiv.appendChild(itemSpan);
              }

              if (Array.isArray(item.related_chunk_ids)) {
                item.related_chunk_ids.forEach(cid => {
                  const chunkSpan = document.createElement('span');
                  chunkSpan.className = 'eval-pill eval-pill-chunk';
                  chunkSpan.textContent = `Chunk: ${cid}`;
                  metaDiv.appendChild(chunkSpan);
                });
              }

              li.appendChild(metaDiv);
            }
          } else {
            li.textContent = String(item);
          }

          unsupportedListEl.appendChild(li);
        });
        unsupportedCardEl.style.display = 'block';
      } else {
        unsupportedCardEl.style.display = 'none';
      }
    }

    // 7. Metadatos Técnicos
    const modelEl = document.getElementById('evalTechModel');
    const evalVerEl = document.getElementById('evalTechEvaluatorVer');
    const rubricVerEl = document.getElementById('evalTechRubricVer');
    const latencyEl = document.getElementById('evalTechLatency');
    const formatIdEl = document.getElementById('evalTechFormatId');
    const evalIdEl = document.getElementById('evalTechEvalId');

    if (modelEl) modelEl.textContent = `Modelo: ${semEval.model || 'Gemini 2.0 (LLM-as-a-Judge)'}`;
    if (evalVerEl) evalVerEl.textContent = `Evaluador: ${evalData.evaluator_version || '2.0.0'}`;
    if (rubricVerEl) rubricVerEl.textContent = `Rúbrica: ${evalData.rubric_version || '2.0.0'}`;
    if (latencyEl) latencyEl.textContent = `Latencia: ${semEval.latency_ms ? semEval.latency_ms + ' ms' : '--'}`;
    if (formatIdEl) formatIdEl.textContent = `Formato: ${evalData.format_id || '--'}`;
    if (evalIdEl) evalIdEl.textContent = `ID: ${evalData.evaluation_id || '--'}`;
  },

  /**
   * Vista informativa cuando un formato todavía no posee evaluación (ej. tldr)
   */
  renderEmptyAttempt(formatData) {
    const bannerEl = document.getElementById('evalVerdictBanner');
    const iconEl = document.getElementById('evalVerdictIcon');
    const titleEl = document.getElementById('evalVerdictTitle');
    const badgeEl = document.getElementById('evalVerdictBadge');
    const descEl = document.getElementById('evalVerdictDesc');
    const fallbackAlertEl = document.getElementById('evalFallbackAlert');

    if (bannerEl) bannerEl.className = 'eval-verdict-banner is-neutral';
    if (iconEl) iconEl.textContent = 'ℹ';
    if (titleEl) titleEl.textContent = 'Evaluación en Proceso / Sin Veredicto';
    if (badgeEl) {
      badgeEl.textContent = 'SIN VEREDICTO';
      badgeEl.className = 'verdict-badge-tag tag-neutral';
    }
    if (descEl) {
      descEl.textContent = 'El Agente Evaluador aún no ha emitido una evaluación técnica ni pedagógica para este formato.';
    }
    if (fallbackAlertEl) fallbackAlertEl.style.display = 'none';

    const heuristicListEl = document.getElementById('evalHeuristicList');
    if (heuristicListEl) {
      heuristicListEl.textContent = '';
      const note = document.createElement('div');
      note.className = 'eval-empty-note';
      note.textContent = 'Puntuaciones heurísticas pendientes de ejecución.';
      heuristicListEl.appendChild(note);
    }

    const semanticListEl = document.getElementById('evalSemanticList');
    if (semanticListEl) {
      semanticListEl.textContent = '';
      const note = document.createElement('div');
      note.className = 'eval-empty-note';
      note.textContent = 'Evaluación semántica pendiente.';
      semanticListEl.appendChild(note);
    }

    const obsSectionEl = document.getElementById('evalObsSection');
    if (obsSectionEl) obsSectionEl.style.display = 'none';

    const recsSectionEl = document.getElementById('evalRecsSection');
    if (recsSectionEl) recsSectionEl.style.display = 'none';

    const unsupportedCardEl = document.getElementById('evalUnsupportedCard');
    if (unsupportedCardEl) unsupportedCardEl.style.display = 'none';

    const formatIdEl = document.getElementById('evalTechFormatId');
    const evalIdEl = document.getElementById('evalTechEvalId');
    if (formatIdEl) formatIdEl.textContent = `Formato: ${formatData?.format_id || '--'}`;
    if (evalIdEl) evalIdEl.textContent = 'ID: --';
  },

  closeModal() {
    if (this.modalOverlay) {
      this.modalOverlay.style.display = 'none';
      this.modalOverlay.classList.remove('active');
    }
  },

  /**
   * Crea una fila de métrica segura con barra de progreso en escala 1.0 a 5.0
   */
  createScoreRow(metricKey, rawValue, themeColor = 'cyan') {
    if (rawValue === null || rawValue === undefined) return null;

    const row = document.createElement('div');
    row.className = 'eval-metric-row';

    // Normalizar valor numérico (soporta escala 1.0 a 5.0 acordada, o 0 a 100 de compatibilidad)
    let numeric = typeof rawValue === 'number' ? rawValue : parseFloat(rawValue);
    if (isNaN(numeric)) return null;

    let percentage = 0;
    let displayVal = '';

    if (numeric <= 5.0) {
      percentage = Math.min(100, Math.max(0, Math.round((numeric / 5.0) * 100)));
      displayVal = `${numeric % 1 === 0 ? numeric : numeric.toFixed(1)} / 5.0`;
    } else {
      percentage = Math.min(100, Math.max(0, Math.round(numeric)));
      displayVal = `${percentage}%`;
    }

    const labelWrap = document.createElement('div');
    labelWrap.className = 'metric-label-wrap';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'metric-name';
    nameSpan.textContent = this.formatMetricName(metricKey);

    const valSpan = document.createElement('span');
    valSpan.className = 'metric-value';
    valSpan.textContent = displayVal;

    labelWrap.appendChild(nameSpan);
    labelWrap.appendChild(valSpan);

    const trackDiv = document.createElement('div');
    trackDiv.className = 'metric-bar-track';

    const fillDiv = document.createElement('div');
    fillDiv.className = `metric-bar-fill fill-${themeColor}`;
    fillDiv.style.width = `${percentage}%`;

    trackDiv.appendChild(fillDiv);
    row.appendChild(labelWrap);
    row.appendChild(trackDiv);

    return row;
  },

  /**
   * Mapea las 4 dimensiones canónicas acordadas en V2 y legacy
   */
  formatMetricName(key) {
    if (!key) return '';
    const dictionary = {
      relevance: 'Relevancia',
      coherence: 'Coherencia',
      didactic_adaptation: 'Adaptación Didáctica',
      content_support: 'Soporte Documental',
      // Soporte retrocompatible
      format_compliance: 'Cumplimiento de Formato',
      schema_validation: 'Validación de Esquema',
      length_check: 'Extensión y Balance',
      question_count: 'Cantidad de Reactivos',
      structure_integrity: 'Integridad Estructural',
      pedagogical_clarity: 'Claridad Didáctica',
      depth_level: 'Profundidad Conceptual',
      factual_alignment: 'Fidelidad al Documento'
    };

    if (dictionary[key]) return dictionary[key];

    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  },

  /**
   * Colección de evaluaciones del último ciclo basada estrictamente en el mock de consenso V2
   */
  getSampleEvaluations(formatKey) {
    if (formatKey === 'quiz') {
      return [
        {
          evaluation_id: 'eval_quiz_002',
          format_id: 'fmt_quiz_corrected',
          created_at: '2026-10-14T18:12:00+00:00',
          verdict: 'approved',
          heuristic_scores: {
            relevance: 5,
            coherence: 5,
            didactic_adaptation: 4,
            content_support: 5
          },
          semantic_evaluation: {
            status: 'success',
            scores: {
              relevance: 4.8,
              coherence: 4.9,
              didactic_adaptation: 4.3,
              content_support: 4.9
            },
            observations: [],
            recommendations: [],
            unsupported_information: [],
            error_code: null,
            error_message: null,
            model: 'semantic-provider (Gemini 2.0)',
            prompt_version: 'v0.1',
            latency_ms: 875
          },
          evaluator_version: '2.0.0',
          rubric_version: '2.0.0'
        },
        {
          evaluation_id: 'eval_quiz_001',
          format_id: 'fmt_quiz_initial',
          created_at: '2026-10-14T18:10:00+00:00',
          verdict: 'requires_revision',
          heuristic_scores: {
            relevance: 4,
            coherence: 4,
            didactic_adaptation: 2,
            content_support: 4
          },
          semantic_evaluation: {
            status: 'success',
            scores: {
              relevance: 4.2,
              coherence: 4.3,
              didactic_adaptation: 2.5,
              content_support: 4.1
            },
            observations: [
              {
                dimension: 'didactic_adaptation',
                severity: 'high',
                message: 'La explicación asume conceptos avanzados para el perfil inicial.',
                item_id: 'q1'
              }
            ],
            recommendations: [
              {
                dimension: 'didactic_adaptation',
                message: 'Explicar primero los conceptos básicos y simplificar la pregunta.',
                item_id: 'q1'
              }
            ],
            unsupported_information: [
              {
                claim: 'REST exige un protocolo propietario.',
                reason: 'Los chunks utilizados no respaldan esa afirmación.',
                item_id: 'q1',
                related_chunk_ids: ['chunk_001']
              }
            ],
            error_code: null,
            error_message: null,
            model: 'semantic-provider (Gemini 2.0)',
            prompt_version: 'v0.1',
            latency_ms: 860
          },
          evaluator_version: '2.0.0',
          rubric_version: '2.0.0'
        }
      ];
    }

    if (formatKey === 'flashcards') {
      return [
        {
          evaluation_id: 'eval_flashcards_001',
          format_id: 'fmt_flashcards_001',
          created_at: '2026-10-14T18:11:00+00:00',
          verdict: 'approved',
          heuristic_scores: {
            relevance: 4,
            coherence: 4,
            didactic_adaptation: 4,
            content_support: 4
          },
          semantic_evaluation: {
            status: 'unavailable',
            scores: null,
            observations: [],
            recommendations: [],
            unsupported_information: [],
            error_code: 'not_configured',
            error_message: null,
            model: null,
            prompt_version: null,
            latency_ms: null
          },
          evaluator_version: '2.0.0',
          rubric_version: '2.0.0'
        }
      ];
    }

    if (formatKey === 'video' || formatKey === 'video_script') {
      return [
        {
          evaluation_id: 'eval_video_001',
          format_id: 'fmt_video_001',
          created_at: '2026-10-14T18:13:00+00:00',
          verdict: null,
          heuristic_scores: null,
          semantic_evaluation: {
            status: 'failed',
            scores: null,
            observations: [],
            recommendations: [],
            unsupported_information: [],
            error_code: 'timeout',
            error_message: null,
            model: null,
            prompt_version: null,
            latency_ms: null
          },
          evaluator_version: '2.0.0',
          rubric_version: '2.0.0'
        }
      ];
    }

    // tldr / sintesis -> ciclo sin evaluación emitida
    return [];
  }
};
