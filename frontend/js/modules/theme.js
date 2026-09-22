/**
 * theme.js
 * Control del tema visual Claro / Oscuro con persistencia en localStorage.
 */

import { state } from '../state.js';
import { CONFIG } from '../config.js';

export const theme = {
  init() {
    const btnTheme = document.getElementById('btnTheme');
    const themeBtnText = document.getElementById('themeBtnText');

    const currentTheme = state.get().theme;
    this.applyTheme(currentTheme);

    if (btnTheme) {
      btnTheme.addEventListener('click', () => {
        const nextTheme = state.get().theme === 'dark' ? 'light' : 'dark';
        this.applyTheme(nextTheme);
      });
    }

    // Actualiza texto de botón si el estado cambia externamente
    state.subscribe((s) => {
      if (themeBtnText) {
        themeBtnText.textContent = s.theme === 'dark' ? 'Modo Claro' : 'Modo Oscuro';
      }
    });
  },

  applyTheme(themeName) {
    document.documentElement.setAttribute('data-theme', themeName);
    localStorage.setItem(CONFIG.STORAGE_KEYS.THEME, themeName);
    state.set({ theme: themeName });

    const themeBtnText = document.getElementById('themeBtnText');
    if (themeBtnText) {
      themeBtnText.textContent = themeName === 'dark' ? 'Modo Claro' : 'Modo Oscuro';
    }
  }
};
