/**
 * router.js
 * Enrutador de vistas de nivel superior (SPA) para alternar entre pestañas.
 */

import { state } from '../state.js';

export const router = {
  views: {},
  tabButtons: {},

  init() {
    this.views = {
      library: document.getElementById('viewLibrary'),
      upload: document.getElementById('viewUpload'),
      study: document.getElementById('viewStudy')
    };

    const navButtons = document.querySelectorAll('.nav-tab-btn');
    navButtons.forEach(btn => {
      const targetTab = btn.getAttribute('data-tab');
      this.tabButtons[targetTab] = btn;

      btn.addEventListener('click', () => {
        this.navigate(targetTab);
      });
    });

    // Escuchar cambios de estado para actualizar vistas
    state.subscribe((s) => {
      this.renderTab(s.activeTab);
    });

    // Renderizar pestaña inicial
    this.renderTab(state.get().activeTab);
  },

  /**
   * Cambia la pestaña activa en el estado global
   * @param {string} tabName ('upload' | 'notebook' | 'study')
   */
  navigate(tabName) {
    if (!this.views[tabName]) return;
    state.set({ activeTab: tabName });
  },

  /**
   * Actualiza el DOM según la pestaña activa
   */
  renderTab(tabName) {
    // Alternar vistas
    Object.keys(this.views).forEach(key => {
      const viewEl = this.views[key];
      if (viewEl) {
        if (key === tabName) {
          viewEl.classList.add('active');
        } else {
          viewEl.classList.remove('active');
        }
      }
    });

    // Alternar botones de navegación
    Object.keys(this.tabButtons).forEach(key => {
      const btnEl = this.tabButtons[key];
      if (btnEl) {
        if (key === tabName) {
          btnEl.classList.add('active');
        } else {
          btnEl.classList.remove('active');
        }
      }
    });

    // Si navegó al cuaderno o al estudio, hacer scroll suave al inicio
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
};
