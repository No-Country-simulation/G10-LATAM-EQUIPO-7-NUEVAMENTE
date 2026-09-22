/**
 * jsonViewer.js
 * Modal interactivo para inspeccionar y copiar el JSON estructurado.
 */

import { state } from '../state.js';

export const jsonViewer = {
  elements: {},

  init() {
    this.elements = {
      modal: document.getElementById('jsonModal'),
      title: document.getElementById('jsonModalTitle'),
      codeDisplay: document.getElementById('jsonCodeDisplay'),
      btnCopy: document.getElementById('btnCopyJson'),
      btnClose: document.getElementById('btnCloseJsonModal')
    };

    if (this.elements.btnClose) {
      this.elements.btnClose.addEventListener('click', () => this.close());
    }

    if (this.elements.btnCopy) {
      this.elements.btnCopy.addEventListener('click', () => this.copyToClipboard());
    }

    if (this.elements.modal) {
      this.elements.modal.addEventListener('click', (e) => {
        if (e.target === this.elements.modal) this.close();
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.code === 'Escape' && state.get().modals.isJsonModalOpen) {
        this.close();
      }
    });
  },

  open(jsonData, titleText) {
    const { modal, title, codeDisplay, btnCopy } = this.elements;
    if (!modal) return;

    if (title) title.textContent = titleText || 'JSON Estructurado (Respuesta RAG)';
    if (codeDisplay) codeDisplay.textContent = JSON.stringify(jsonData, null, 2);

    if (btnCopy) {
      btnCopy.textContent = 'Copiar JSON';
      btnCopy.classList.remove('copied');
    }

    modal.style.display = 'flex';
    state.set({
      modals: {
        ...state.get().modals,
        isJsonModalOpen: true
      }
    });
  },

  close() {
    if (this.elements.modal) {
      this.elements.modal.style.display = 'none';
    }
    state.set({
      modals: {
        ...state.get().modals,
        isJsonModalOpen: false
      }
    });
  },

  copyToClipboard() {
    const text = this.elements.codeDisplay?.textContent;
    if (!text) return;

    navigator.clipboard.writeText(text).then(() => {
      if (this.elements.btnCopy) {
        this.elements.btnCopy.textContent = '✓ ¡Copiado!';
        this.elements.btnCopy.classList.add('copied');
        setTimeout(() => {
          this.elements.btnCopy.textContent = 'Copiar JSON';
          this.elements.btnCopy.classList.remove('copied');
        }, 2000);
      }
    });
  }
};
