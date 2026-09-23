/**
 * summary.js
 * Lógica para la visualización del formato Síntesis / Resumen Ejecutivo RAG.
 */

export const summary = {
  elements: {},

  init() {
    this.elements = {
      resumenText: document.getElementById('sintesisResumen'),
      puntosList: document.getElementById('sintesisPuntosList'),
      chipsContainer: document.getElementById('sintesisTerminosChips')
    };
  },

  render(sintesisData) {
    const { resumenText, puntosList, chipsContainer } = this.elements;
    if (!resumenText || !puntosList || !chipsContainer) return;

    if (!sintesisData) {
      resumenText.textContent = 'Síntesis no disponible.';
      puntosList.innerHTML = '';
      chipsContainer.innerHTML = '';
      return;
    }

    resumenText.textContent = sintesisData.resumen_ejecutivo || 'Resumen generado automáticamente.';
    
    const puntos = sintesisData.puntos_clave || [];
    puntosList.innerHTML = puntos.map(p => `<li>${p}</li>`).join('');

    const terminos = sintesisData.terminos_clave || [];
    chipsContainer.innerHTML = terminos.map(t => `<span class="concept-chip">${t}</span>`).join('');
  }
};
