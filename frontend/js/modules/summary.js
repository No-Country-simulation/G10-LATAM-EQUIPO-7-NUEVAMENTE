/**
 * summary.js
 * Lógica para la visualización del formato Síntesis Ejecutiva (TLDR) RAG.
 * Contrato canónico Backend PR #71 (TLDRContentResponse: title, summary, key_points, conclusion).
 * Manejo de estados (processing, pending, failed, no_results, success) y regeneración individual.
 */

import { toFriendlyError } from '../utils/friendlyError.js';

export const summary = {
  elements: {},
  meta: {
    status: 'success',
    errorMessage: null,
    formatId: null
  },

  init() {
    this.elements = {
      titleText: document.getElementById('sintesisTitle'),
      resumenText: document.getElementById('sintesisResumen'),
      conclusionBox: document.getElementById('sintesisConclusionBox'),
      conclusionText: document.getElementById('sintesisConclusion'),
      puntosList: document.getElementById('sintesisPuntosList'),
      chipsContainer: document.getElementById('sintesisTerminosChips'),
      terminosSection: document.getElementById('sintesisTerminosSection'),
      counterBadge: document.getElementById('sintesisCounterBadge'),
      btnRegen: document.getElementById('btnRegenSintesis')
    };

    if (this.elements.btnRegen) {
      this.elements.btnRegen.addEventListener('click', () => {
        import('./studyHub.js').then(({ studyHub }) => {
          studyHub.triggerRegeneration(['tldr']);
        });
      });
    }
  },

  render(sintesisData) {
    const {
      titleText,
      resumenText,
      conclusionBox,
      conclusionText,
      puntosList,
      chipsContainer,
      terminosSection,
      counterBadge,
      btnRegen
    } = this.elements;

    if (!resumenText || !puntosList) return;

    this.meta = {
      status: sintesisData?.status || (sintesisData ? 'success' : 'empty'),
      errorMessage: sintesisData?.error_message || null,
      formatId: sintesisData?.format_id || null
    };

    const isBusy = this.meta.status === 'processing' || this.meta.status === 'pending';
    if (btnRegen) {
      btnRegen.disabled = isBusy;
    }

    // Caso 1: En procesamiento o pendiente en el servidor
    if (isBusy) {
      if (counterBadge) counterBadge.textContent = 'Generando...';
      if (titleText) titleText.textContent = 'Síntesis Ejecutiva (TLDR)';
      resumenText.textContent = 'El pipeline de IA está extrayendo los conceptos y redactando la síntesis ejecutiva a partir del documento indexado. Por favor espera unos instantes.';
      puntosList.innerHTML = '';
      if (conclusionBox) conclusionBox.style.display = 'none';
      if (terminosSection) terminosSection.style.display = 'none';
      return;
    }

    // Caso 2: Fallo en la generación del formato
    if (this.meta.status === 'failed') {
      const friendly = toFriendlyError({ message: this.meta.errorMessage });
      if (counterBadge) counterBadge.textContent = 'Síntesis (Fallo)';
      if (titleText) titleText.textContent = 'Síntesis Ejecutiva No Disponible';
      resumenText.textContent = friendly.message || 'No fue posible generar la síntesis ejecutiva en este momento.';

      puntosList.innerHTML = '';
      const noticeCard = document.createElement('div');
      noticeCard.className = 'format-friendly-notice';

      const iconEl = document.createElement('div');
      iconEl.className = 'friendly-notice-icon';
      iconEl.textContent = '⚠️';

      const titleEl = document.createElement('h4');
      titleEl.className = 'friendly-notice-title';
      titleEl.textContent = friendly.title || 'Error al Generar Síntesis';

      const textEl = document.createElement('p');
      textEl.className = 'friendly-notice-text';
      textEl.textContent = friendly.message || 'La IA no pudo completar el resumen. Puedes solicitar un nuevo intento.';

      const actionsEl = document.createElement('div');
      actionsEl.className = 'friendly-notice-actions';

      const btnRetry = document.createElement('button');
      btnRetry.type = 'button';
      btnRetry.className = 'btn-friendly-action';
      const retrySpan = document.createElement('span');
      retrySpan.textContent = 'Reintentar Síntesis';
      btnRetry.appendChild(retrySpan);
      btnRetry.addEventListener('click', () => {
        import('./studyHub.js').then(({ studyHub }) => {
          studyHub.triggerRegeneration(['tldr']);
        });
      });

      actionsEl.appendChild(btnRetry);
      noticeCard.appendChild(iconEl);
      noticeCard.appendChild(titleEl);
      noticeCard.appendChild(textEl);
      noticeCard.appendChild(actionsEl);

      puntosList.appendChild(noticeCard);
      if (conclusionBox) conclusionBox.style.display = 'none';
      if (terminosSection) terminosSection.style.display = 'none';
      return;
    }

    // Caso 3: Sin contenido o sin resultados
    if (this.meta.status === 'no_results' || !sintesisData) {
      if (counterBadge) counterBadge.textContent = 'Síntesis Ejecutiva';
      if (titleText) titleText.textContent = 'Síntesis Ejecutiva';
      resumenText.textContent = 'El documento no contiene suficiente información para formular una síntesis ejecutiva.';
      puntosList.innerHTML = '';
      if (conclusionBox) conclusionBox.style.display = 'none';
      if (terminosSection) terminosSection.style.display = 'none';
      return;
    }

    // Caso 4: Éxito (Soporta content anidado canónico o raíz)
    const content = sintesisData.content || sintesisData;
    const title = content.title || 'Resumen Ejecutivo';
    const summaryText = content.summary || content.executive_summary || content.resumen_ejecutivo || 'Resumen generado automáticamente.';
    const keyPoints = Array.isArray(content.key_points)
      ? content.key_points
      : (Array.isArray(content.key_takeaways) ? content.key_takeaways : (Array.isArray(content.puntos_clave) ? content.puntos_clave : []));
    const conclusion = content.conclusion || content.conclusion_formativa || null;

    if (counterBadge) counterBadge.textContent = 'Síntesis Ejecutiva (TLDR)';
    if (titleText) titleText.textContent = title;
    resumenText.textContent = summaryText;

    // Renderizado seguro de puntos críticos
    puntosList.innerHTML = '';
    if (keyPoints.length > 0) {
      keyPoints.forEach(point => {
        const li = document.createElement('li');
        li.textContent = typeof point === 'string' ? point : String(point ?? '');
        puntosList.appendChild(li);
      });
    } else {
      const li = document.createElement('li');
      li.textContent = 'Conceptos esenciales del documento indexados exitosamente.';
      puntosList.appendChild(li);
    }

    // Renderizado seguro de conclusión
    if (conclusionBox && conclusionText) {
      if (conclusion) {
        conclusionBox.style.display = 'flex';
        conclusionText.textContent = conclusion;
      } else {
        conclusionBox.style.display = 'none';
      }
    }

    // Competencias o términos clave si están presentes
    const terminos = content.key_terms || content.terminos_clave || [];
    if (terminosSection && chipsContainer) {
      if (Array.isArray(terminos) && terminos.length > 0) {
        terminosSection.style.display = 'block';
        chipsContainer.innerHTML = '';
        terminos.forEach(term => {
          const chip = document.createElement('span');
          chip.className = 'concept-chip';
          chip.textContent = typeof term === 'string' ? term : String(term ?? '');
          chipsContainer.appendChild(chip);
        });
      } else {
        terminosSection.style.display = 'none';
      }
    }
  }
};
