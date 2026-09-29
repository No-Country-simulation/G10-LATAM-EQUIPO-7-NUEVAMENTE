/**
 * main.js
 * Punto de entrada principal y bootstrap modular de la aplicación NuevaMente.
 */

import { state } from './state.js';
import { CONFIG } from './config.js';
import { router } from './modules/router.js';
import { uploadTab } from './modules/uploadTab.js';
import { studyHub } from './modules/studyHub.js';
import { bookshelf } from './modules/bookshelf.js';
import { portada } from './modules/portada.js';
import { statusDialog } from './modules/statusDialog.js';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicializar Diálogo Temporal de Estados / Errores
  statusDialog.init();

  // 2. Inicializar Enrutador de Pestañas Principales (3 Pilares)
  router.init();

  // 3. Inicializar La Biblioteca de NuevaMente
  bookshelf.init();

  // 4. Inicializar Portada de Bienvenida
  portada.init();

  // 5. Inicializar Pestaña de Ingesta & Pipeline RAG
  uploadTab.init();

  // 6. Inicializar Centro de Estudio Multi-Formato
  studyHub.init();

  // 7. Configurar Selector de Modo de Conexión (Mock vs Real)
  setupApiModeSelector();

  // 8. Suscribir estado al footer de estado
  setupSystemStatusBar();

  // 9. Mostrar y permitir configurar la URL del Backend en el header
  setupBackendBadge();
});

function setupApiModeSelector() {
  const apiModeSelector = document.getElementById('apiModeSelector');
  if (!apiModeSelector) return;

  apiModeSelector.value = state.get().apiMode;

  apiModeSelector.addEventListener('change', (e) => {
    const newMode = e.target.value;
    state.set({ apiMode: newMode });
    localStorage.setItem(CONFIG.STORAGE_KEYS.API_MODE, newMode);
  });
}

function setupSystemStatusBar() {
  const ociStatusText = document.getElementById('ociStatusText');
  const qualityScoreText = document.getElementById('qualityScoreText');

  state.subscribe((s) => {
    const doc = s.currentDocument;
    if (ociStatusText) {
      ociStatusText.textContent = s.apiMode === 'real'
        ? 'Conectado al servidor'
        : 'Modo sin conexión (datos de ejemplo)';
    }

    if (qualityScoreText) {
      qualityScoreText.textContent = doc
        ? `Estudiando: ${doc.title}`
        : 'Explorando la biblioteca';
    }
  });
}

function setupBackendBadge() {
  const badge = document.querySelector('.header-connection-badge');
  if (!badge) return;
  badge.title = `Conectado a Backend API: ${CONFIG.API.DEFAULT_BASE_URL} (Clic para cambiar)`;
  badge.style.cursor = 'pointer';
  badge.addEventListener('click', () => {
    const current = CONFIG.API.DEFAULT_BASE_URL;
    const nextUrl = prompt('Configurar URL del Backend (FastAPI):', current);
    if (nextUrl !== null && nextUrl.trim() !== current) {
      if (typeof window.setBackendUrl === 'function') {
        window.setBackendUrl(nextUrl.trim());
      }
    }
  });
}
