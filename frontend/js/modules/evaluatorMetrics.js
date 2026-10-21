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
  cycleItems: [],
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

    // Regla de Negocio (PR #110 Backend):
    // El indicador principal de calidad utiliza EXCLUSIVAMENTE 'evaluation', correspondiente
    // a la versión del contenido que se está mostrando. NUNCA tomar evaluations[0] automáticamente
    // como fallback, ya que podría pertenecer a una versión previa u original y no a la vigente.
    const evaluation = formatData.evaluation || null;

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
        badgeBtn.title = 'El Agente Evaluador certificó esta versión del formato. Clic para ver métricas completas.';
      } else if (verdict === 'requires_revision') {
        badgeBtn.classList.add('verdict-requires-revision');
        textSpan.textContent = 'Requiere Revisión Didáctica';
        badgeBtn.title = 'Esta versión presenta observaciones pedagógicas. Clic para ver detalles e historial.';
      } else if (verdict === 'rejected') {
        badgeBtn.classList.add('verdict-rejected');
        textSpan.textContent = 'Calidad Observada (No Aprobado)';
        badgeBtn.title = 'Esta versión no superó la rúbrica mínima. Clic para auditar e historial.';
      } else {
        // verdict === null
        badgeBtn.classList.add('verdict-preview');
        textSpan.textContent = semStatus === 'failed' ? 'Evaluación Incompleta' : 'En Evaluación Pedagógica';
        badgeBtn.title = 'Evaluación técnica registrada sin veredicto definitivo. Clic para inspeccionar.';
      }
    } else {
      // Si evaluation llega null, debe indicar estrictamente: «Sin evaluación de esta versión»
      badgeBtn.classList.add('verdict-unevaluated');
      textSpan.textContent = 'Sin evaluación de esta versión';
      badgeBtn.title = 'Esta versión del formato aún no cuenta con evaluación pedagógica. Clic para consultar detalles e historial.';
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

    // Construir la lista de versiones/evaluaciones del ciclo identificando cada una por su format_id
    this.buildCycleItems(formatData, evaluationData);

    // Por defecto siempre posicionar en la versión vigente (índice 0)
    this.activeAttemptIndex = 0;

    // Renderizar selector de historial de versiones
    this.renderCycleSelector();

    // Renderizar la versión seleccionada
    const selectedItem = this.cycleItems[this.activeAttemptIndex] || null;
    this.renderCycleItem(selectedItem, formatKey, formatData);

    // Mostrar modal
    if (this.modalOverlay) {
      this.modalOverlay.style.display = 'flex';
      this.modalOverlay.classList.add('active');
    }
  },

  /**
   * Construye la lista de versiones y evaluaciones disponibles en formatData.
   * Agrupa y distingue cada versión por su format_id, conservando TODAS las evaluaciones
   * que compartan dicho identificador (diferenciadas por evaluation_id) sin descartar ninguna.
   * Si la versión vigente no tiene evaluación (evaluation === null), se presenta en estado no evaluado
   * permitiendo al mismo tiempo consultar el historial completo de evaluaciones.
   */
  buildCycleItems(formatData, currentEvaluation) {
    const currentFormatId = formatData?.format_id || currentEvaluation?.format_id || null;
    const currentEvalId = currentEvaluation?.evaluation_id || null;
    const allEvals = Array.isArray(formatData?.evaluations) ? formatData.evaluations : [];

    // 1. Recolectar todas las evaluaciones sin descartar ninguna (deduplicando únicamente instancias idénticas por evaluation_id)
    const evalsPool = [];
    const seenEvalIds = new Set();

    if (currentEvaluation) {
      evalsPool.push(currentEvaluation);
      if (currentEvaluation.evaluation_id) {
        seenEvalIds.add(currentEvaluation.evaluation_id);
      }
    }

    for (const ev of allEvals) {
      if (!ev) continue;
      if (ev.evaluation_id && seenEvalIds.has(ev.evaluation_id)) {
        continue;
      }
      if (ev.evaluation_id) {
        seenEvalIds.add(ev.evaluation_id);
      }
      evalsPool.push(ev);
    }

    // 2. Agrupar evaluaciones por format_id para conservar la separación por versiones
    const groupsByFormat = new Map();

    // Si conocemos el format_id vigente, inicializarlo primero para que sea el grupo principal
    if (currentFormatId) {
      groupsByFormat.set(currentFormatId, []);
    }

    for (const ev of evalsPool) {
      const fId = ev.format_id || currentFormatId || 'default_format';
      if (!groupsByFormat.has(fId)) {
        groupsByFormat.set(fId, []);
      }
      groupsByFormat.get(fId).push(ev);
    }

    // Si el formato vigente no tenía evaluaciones en el pool, se mantiene la entrada vacía en groupsByFormat
    const distinctFormatIds = Array.from(groupsByFormat.keys());
    const hasMultipleFormats = distinctFormatIds.length > 1;

    const formatShortId = (id) => {
      if (!id) return '';
      return id.length > 12 ? `${id.slice(0, 10)}…` : id;
    };

    const items = [];

    // 3. Generar elementos del historial por cada grupo de format_id
    distinctFormatIds.forEach((fId) => {
      const isCurrentFormat = fId === currentFormatId;
      const evalsInGroup = groupsByFormat.get(fId) || [];

      // Ordenar cronológicamente si traen timestamp
      evalsInGroup.sort((a, b) => {
        const tA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const tB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return tA - tB;
      });

      // Etiqueta base de la versión
      let baseVersionLabel;
      if (isCurrentFormat) {
        baseVersionLabel = hasMultipleFormats ? 'Versión Corregida' : 'Versión Vigente';
      } else {
        const historicalFormatIds = distinctFormatIds.filter(id => id !== currentFormatId);
        const histIndex = historicalFormatIds.indexOf(fId);
        baseVersionLabel = histIndex === 0 ? 'Versión Original' : `Versión Previa ${histIndex + 1}`;
      }

      // Caso A: Formato vigente sin evaluación activa (currentEvaluation === null)
      if (isCurrentFormat && !currentEvaluation) {
        // Elemento que representa la versión vigente sin evaluación
        items.push({
          isCurrent: true,
          versionLabel: `${baseVersionLabel} (Vigente)`,
          baseVersion: baseVersionLabel,
          format_id: fId,
          shortFormatId: formatShortId(fId),
          evaluation_id: null,
          hasEvaluation: false,
          evaluation: null
        });

        // Si existen otras evaluaciones históricas vinculadas a este mismo format_id, incluirlas sin descartarlas
        evalsInGroup.forEach((ev, evIdx) => {
          const attemptNum = evIdx + 1;
          const attemptSuffix = evalsInGroup.length > 1 ? ` · Intento ${attemptNum}` : ' · Evaluación previa';
          items.push({
            isCurrent: false,
            versionLabel: `${baseVersionLabel}${attemptSuffix}`,
            baseVersion: baseVersionLabel,
            format_id: fId,
            shortFormatId: formatShortId(fId),
            evaluation_id: ev.evaluation_id || null,
            hasEvaluation: true,
            evaluation: ev
          });
        });
        return;
      }

      // Caso B: Grupo sin evaluaciones (placeholder de seguridad)
      if (evalsInGroup.length === 0) {
        if (isCurrentFormat) {
          items.push({
            isCurrent: true,
            versionLabel: `${baseVersionLabel} (Vigente)`,
            baseVersion: baseVersionLabel,
            format_id: fId,
            shortFormatId: formatShortId(fId),
            evaluation_id: null,
            hasEvaluation: false,
            evaluation: null
          });
        }
        return;
      }

      // Caso C: Grupo con una o más evaluaciones (conservando todas las evaluaciones)
      const hasMultipleInGroup = evalsInGroup.length > 1;

      evalsInGroup.forEach((ev, evIdx) => {
        const attemptNum = evIdx + 1;
        const isThisCurrentEval = isCurrentFormat && (
          (currentEvalId && ev.evaluation_id === currentEvalId) ||
          (ev === currentEvaluation) ||
          (!currentEvalId && evIdx === evalsInGroup.length - 1)
        );

        let label;
        if (isCurrentFormat) {
          if (isThisCurrentEval) {
            label = hasMultipleInGroup
              ? `${baseVersionLabel} (Vigente) · Intento ${attemptNum}`
              : `${baseVersionLabel} (Vigente)`;
          } else {
            label = `${baseVersionLabel} · Intento ${attemptNum}`;
          }
        } else {
          label = hasMultipleInGroup
            ? `${baseVersionLabel} · Intento ${attemptNum}`
            : baseVersionLabel;
        }

        items.push({
          isCurrent: isThisCurrentEval,
          versionLabel: label,
          baseVersion: baseVersionLabel,
          format_id: fId,
          shortFormatId: formatShortId(fId),
          evaluation_id: ev.evaluation_id || null,
          hasEvaluation: true,
          evaluation: ev
        });
      });
    });

    // Asegurar que el elemento marcado como isCurrent esté al frente (índice 0)
    const curIdx = items.findIndex(item => item.isCurrent);
    if (curIdx > 0) {
      const [current] = items.splice(curIdx, 1);
      items.unshift(current);
    }

    this.cycleItems = items;
  },

  /**
   * Renderiza el selector de versiones e historial de evaluaciones en el modal
   */
  renderCycleSelector() {
    const cycleBar = document.getElementById('evalCycleBar');
    if (!cycleBar) return;

    cycleBar.textContent = ''; // Limpieza segura DOM

    const list = this.cycleItems || [];
    if (list.length <= 1) {
      cycleBar.style.display = 'none';
      return;
    }

    cycleBar.style.display = 'flex';

    const labelSpan = document.createElement('span');
    labelSpan.className = 'eval-cycle-label';
    labelSpan.textContent = 'Historial de Versiones:';
    cycleBar.appendChild(labelSpan);

    list.forEach((item, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `eval-cycle-btn${index === this.activeAttemptIndex ? ' is-active' : ''}`;

      // Etiqueta de la versión
      const textSpan = document.createElement('span');
      textSpan.textContent = item.versionLabel;
      btn.appendChild(textSpan);

      // Chip con format_id para identificación técnica
      if (item.shortFormatId) {
        const fmtChip = document.createElement('span');
        fmtChip.className = 'eval-cycle-fmt';
        fmtChip.textContent = item.shortFormatId;
        if (item.format_id) {
          fmtChip.title = `ID de formato: ${item.format_id}${item.evaluation_id ? ' · ID de evaluación: ' + item.evaluation_id : ''}`;
        }
        btn.appendChild(fmtChip);
      }

      // Veredicto en miniatura (punto de color)
      const dot = document.createElement('span');
      dot.className = 'eval-badge-dot';
      dot.style.marginLeft = '0.35rem';

      const evalSuffix = item.evaluation_id ? ` · Eval: ${item.evaluation_id}` : '';
      if (item.hasEvaluation && item.evaluation) {
        const v = (item.evaluation.verdict || 'none').toLowerCase();
        if (v === 'approved') {
          dot.style.background = '#10b981';
          btn.title = `${item.versionLabel} · Aprobado${evalSuffix}`;
        } else if (v === 'requires_revision') {
          dot.style.background = '#f59e0b';
          btn.title = `${item.versionLabel} · Requiere Revisión${evalSuffix}`;
        } else if (v === 'rejected') {
          dot.style.background = '#ef4444';
          btn.title = `${item.versionLabel} · No Aprobado${evalSuffix}`;
        } else {
          dot.style.background = '#94a3b8';
          btn.title = `${item.versionLabel} · En Evaluación${evalSuffix}`;
        }
      } else {
        dot.style.background = '#64748b';
        btn.title = `${item.versionLabel} · Sin evaluación de esta versión`;
      }
      btn.appendChild(dot);

      btn.addEventListener('click', (e) => {
        e.preventDefault();
        this.activeAttemptIndex = index;
        this.renderCycleSelector();
        this.renderCycleItem(list[index], this.activeFormatKey, this.currentFormatData);
      });

      cycleBar.appendChild(btn);
    });
  },

  /**
   * Renderiza el elemento de ciclo seleccionado (vigente o histórico)
   */
  renderCycleItem(cycleItem, formatKey, formatData) {
    if (!cycleItem || !cycleItem.hasEvaluation || !cycleItem.evaluation) {
      this.renderEmptyAttempt(cycleItem, formatData);
    } else {
      this.renderAttempt(cycleItem.evaluation, formatKey, formatData, cycleItem);
    }
  },

  /**
   * Puebla los datos de un intento específico de evaluación en el modal
   */
  renderAttempt(evalData, formatKey, formatData, cycleItem = null) {
    // Si no hay evaluación disponible (ej. tldr en phase evaluating)
    if (!evalData) {
      this.renderEmptyAttempt(cycleItem, formatData);
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
    const displayFmtId = cycleItem?.format_id || evalData.format_id || formatData?.format_id || '--';
    const versionSuffix = cycleItem?.versionLabel ? ` (${cycleItem.versionLabel})` : '';
    if (formatIdEl) formatIdEl.textContent = `Formato: ${displayFmtId}${versionSuffix}`;
    if (evalIdEl) evalIdEl.textContent = `ID: ${evalData.evaluation_id || '--'}`;
  },

  /**
   * Vista informativa cuando un formato o versión todavía no posee evaluación
   */
  renderEmptyAttempt(cycleItem, formatData) {
    const bannerEl = document.getElementById('evalVerdictBanner');
    const iconEl = document.getElementById('evalVerdictIcon');
    const titleEl = document.getElementById('evalVerdictTitle');
    const badgeEl = document.getElementById('evalVerdictBadge');
    const descEl = document.getElementById('evalVerdictDesc');
    const fallbackAlertEl = document.getElementById('evalFallbackAlert');

    if (bannerEl) bannerEl.className = 'eval-verdict-banner is-neutral';
    if (iconEl) iconEl.textContent = 'ℹ';
    if (titleEl) titleEl.textContent = 'Sin evaluación de esta versión';
    if (badgeEl) {
      badgeEl.textContent = 'SIN EVALUACIÓN';
      badgeEl.className = 'verdict-badge-tag tag-neutral';
    }
    if (descEl) {
      const isCorrected = cycleItem?.versionLabel && cycleItem.versionLabel.toLowerCase().includes('corregid');
      if (isCorrected) {
        descEl.textContent = 'Esta versión corregida aún no cuenta con evaluación pedagógica. Puedes consultar en el selector superior la evaluación de la versión original.';
      } else {
        descEl.textContent = 'Esta versión del formato aún no cuenta con evaluación pedagógica emitida por el Agente Evaluador.';
      }
    }
    if (fallbackAlertEl) fallbackAlertEl.style.display = 'none';

    const heuristicListEl = document.getElementById('evalHeuristicList');
    if (heuristicListEl) {
      heuristicListEl.textContent = '';
      const note = document.createElement('div');
      note.className = 'eval-empty-note';
      note.textContent = 'Puntuaciones heurísticas pendientes de evaluación para esta versión.';
      heuristicListEl.appendChild(note);
    }

    const semanticListEl = document.getElementById('evalSemanticList');
    if (semanticListEl) {
      semanticListEl.textContent = '';
      const note = document.createElement('div');
      note.className = 'eval-empty-note';
      note.textContent = 'Evaluación semántica pendiente para esta versión.';
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
    const displayFmtId = cycleItem?.format_id || formatData?.format_id || '--';
    const versionSuffix = cycleItem?.versionLabel ? ` (${cycleItem.versionLabel})` : '';
    if (formatIdEl) formatIdEl.textContent = `Formato: ${displayFmtId}${versionSuffix}`;
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
  }
};

