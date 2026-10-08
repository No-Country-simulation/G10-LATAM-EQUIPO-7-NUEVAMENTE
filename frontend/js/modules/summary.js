/**
 * summary.js
 * Visualización del formato Síntesis Ejecutiva / TLDR (PR #71 BackendAPI).
 * Soporta contrato oficial TLDRContentResponse { title, summary, key_points, conclusion }.
 */

import { toFriendlyError } from '../utils/friendlyError.js';

export const summary = {
  elements: {},
  tldrMeta: null,

  init() {
    this.elements = {
      mainContent: document.getElementById('sintesisMainContent'),
      noticeContainer: document.getElementById('sintesisNoticeContainer'),
      counterBadge: document.getElementById('sintesisCounterBadge'),
      btnRegenSintesis: document.getElementById('btnRegenSintesis'),
      titleHeader: document.getElementById('sintesisTitleHeader'),
      resumenText: document.getElementById('sintesisResumen'),
      conclusionBox: document.getElementById('sintesisConclusionBox'),
      conclusionText: document.getElementById('sintesisConclusion'),
      puntosList: document.getElementById('sintesisPuntosList'),
      chipsContainer: document.getElementById('sintesisTerminosChips'),
      terminosSection: document.getElementById('sintesisTerminosSection')
    };

    if (this.elements.btnRegenSintesis) {
      this.elements.btnRegenSintesis.addEventListener('click', () => {
        import('./studyHub.js').then(({ studyHub }) => {
          studyHub.triggerRegeneration(['tldr']);
        });
      });
    }
  },

  render(tldrData) {
    const {
      mainContent, noticeContainer, counterBadge, btnRegenSintesis,
      titleHeader, resumenText, conclusionBox, conclusionText,
      puntosList, chipsContainer, terminosSection
    } = this.elements;

    if (!mainContent) return;

    this.tldrMeta = {
      status: tldrData?.status || (tldrData?.content ? 'success' : (tldrData ? 'success' : 'empty')),
      errorMessage: tldrData?.error_message || null,
      title: tldrData?.content?.title || tldrData?.title || null
    };

    if (btnRegenSintesis) {
      const isBusy = this.tldrMeta.status === 'processing' || this.tldrMeta.status === 'pending';
      btnRegenSintesis.disabled = isBusy;
    }

    if (counterBadge) {
      if (this.tldrMeta.status === 'processing' || this.tldrMeta.status === 'pending') {
        counterBadge.textContent = 'Generando TLDR...';
      } else {
        counterBadge.textContent = 'Síntesis Ejecutiva';
      }
    }

    // Manejo de Estados Especiales: failed, processing, pending, no_results o empty
    if (!tldrData || this.tldrMeta.status === 'failed' || this.tldrMeta.status === 'processing' || this.tldrMeta.status === 'pending' || this.tldrMeta.status === 'no_results' || this.tldrMeta.status === 'empty') {
      if (mainContent) mainContent.style.display = 'none';
      if (noticeContainer) {
        noticeContainer.style.display = 'block';
        noticeContainer.textContent = ''; // Limpieza segura

        if (this.tldrMeta.status === 'failed') {
          const friendly = toFriendlyError({ message: this.tldrMeta.errorMessage });
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const iconEl = document.createElement('div');
          iconEl.className = 'friendly-notice-icon';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = friendly.title || 'Síntesis No Disponible';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = friendly.message || 'No fue posible generar la síntesis ejecutiva.';

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
          noticeContainer.appendChild(noticeCard);
        } else if (this.tldrMeta.status === 'processing' || this.tldrMeta.status === 'pending') {
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = 'Generando Síntesis Ejecutiva...';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = 'El pipeline de IA está extrayendo los puntos neurálgicos, resumen y conclusión del material indexado.';

          noticeCard.appendChild(titleEl);
          noticeCard.appendChild(textEl);
          noticeContainer.appendChild(noticeCard);
        } else if (this.tldrMeta.status === 'no_results') {
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = 'Sin Síntesis Generada';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = 'El documento no contiene suficiente densidad informativa para elaborar una síntesis ejecutiva.';

          noticeCard.appendChild(titleEl);
          noticeCard.appendChild(textEl);
          noticeContainer.appendChild(noticeCard);
        } else {
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = 'Síntesis en Espera';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = 'La síntesis ejecutiva se generará a partir del material corporativo cargado.';

          noticeCard.appendChild(titleEl);
          noticeCard.appendChild(textEl);
          noticeContainer.appendChild(noticeCard);
        }
      }
      return;
    }

    // Estado Exitoso: Renderizado de datos del contrato oficial (PR #71)
    if (noticeContainer) noticeContainer.style.display = 'none';
    if (mainContent) mainContent.style.display = 'grid';

    const content = tldrData.content || tldrData;
    const title = content.title || this.tldrMeta.title || 'Resumen Ejecutivo';
    const summaryText = content.summary || content.resumen_ejecutivo || content.executive_summary || 'Resumen no disponible.';
    const keyPoints = Array.isArray(content.key_points) ? content.key_points : (Array.isArray(content.puntos_clave) ? content.puntos_clave : []);
    const conclusion = content.conclusion || content.conclusion_operativa || null;
    const keyTerms = Array.isArray(content.key_terms) ? content.key_terms : (Array.isArray(content.terminos_clave) ? content.terminos_clave : []);

    if (titleHeader) {
      titleHeader.textContent = title;
    }

    if (resumenText) {
      resumenText.textContent = summaryText;
    }

    // Puntos Clave
    if (puntosList) {
      puntosList.textContent = '';
      if (keyPoints.length > 0) {
        keyPoints.forEach(p => {
          const li = document.createElement('li');
          li.textContent = typeof p === 'string' ? p : String(p ?? '');
          puntosList.appendChild(li);
        });
      } else {
        const li = document.createElement('li');
        li.textContent = 'Estructura procesada según el protocolo de síntesis pedagógica.';
        puntosList.appendChild(li);
      }
    }

    // Conclusión Operativa (PR #71: TLDRContentResponse.conclusion)
    if (conclusionBox && conclusionText) {
      if (conclusion && conclusion.trim()) {
        conclusionBox.style.display = 'block';
        conclusionText.textContent = conclusion;
      } else {
        conclusionBox.style.display = 'none';
      }
    }

    // Términos o Competencias Clave (opcional si están presentes)
    if (chipsContainer && terminosSection) {
      chipsContainer.textContent = '';
      if (keyTerms.length > 0) {
        terminosSection.style.display = 'block';
        keyTerms.forEach(t => {
          const chip = document.createElement('span');
          chip.className = 'concept-chip';
          chip.textContent = typeof t === 'string' ? t : String(t ?? '');
          chipsContainer.appendChild(chip);
        });
      } else {
        terminosSection.style.display = 'none';
      }
    }
  }
};
