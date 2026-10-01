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
import { backendStatus } from './modules/backendStatus.js';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicializar Diálogo Temporal de Estados / Errores
  statusDialog.init();

  // 2. Inicializar Enrutador de Pestañas Principales
  router.init();
  window.router = router;

  // 3. Inicializar La Biblioteca de NuevaMente
  bookshelf.init();

  // 4. Inicializar Portada / Inicio Cósmico
  portada.init();

  // 5. Inicializar Pestaña de Ingesta & Pipeline RAG
  uploadTab.init();

  // 6. Inicializar Centro de Estudio Multi-Formato
  studyHub.init();

  // 7. Inicializar Monitor en Tiempo Real de Backend FastAPI
  backendStatus.init();

  // 8. Suscribir estado al footer de estado
  setupSystemStatusBar();
});

function setupSystemStatusBar() {
  const ociStatusText = document.getElementById('ociStatusText');
  const qualityScoreText = document.getElementById('qualityScoreText');

  state.subscribe((s) => {
    const doc = s.currentDocument;
    if (ociStatusText) {
      ociStatusText.textContent = 'Conectado al servidor (FastAPI)';
    }

    if (qualityScoreText) {
      qualityScoreText.textContent = doc
        ? `Estudiando: ${doc.title}`
        : 'Explorando Mundos de Estudio';
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
