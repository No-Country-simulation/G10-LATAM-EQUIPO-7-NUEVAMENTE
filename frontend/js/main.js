/**
 * main.js
 * Punto de entrada principal y bootstrap modular de la aplicación NuevaMente.
 */

import { state } from './state.js';
import { CONFIG } from './config.js';
import { apiClient } from './api/apiClient.js';
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

  // 7. Suscribir estado al footer de estado reactivo (Verde = Conectado / Rojo = Desconectado)
  setupSystemStatusBar();

  // 8. Mostrar y permitir configurar la URL del Backend en el header con indicador reactivo
  setupBackendBadge();

  // 9. Chequeo de salud del backend inmediato y periódico (cada 60 segundos)
  apiClient.checkHealth();
  setInterval(() => {
    apiClient.checkHealth();
  }, 60000);

  // 10. Captura global de excepciones y promesas no controladas (Resiliencia en tiempo de ejecución)
  window.addEventListener('unhandledrejection', (event) => {
    console.warn('[Global] Promesa no controlada interceptada:', event.reason);
    event.preventDefault();
  });

  window.addEventListener('error', (event) => {
    console.warn('[Global] Excepción no controlada interceptada:', event.message);
  });
});

function setupSystemStatusBar() {
  const statusIndicator = document.querySelector('.system-status-bar .status-indicator');
  const ociStatusText = document.getElementById('ociStatusText');
  const qualityScoreText = document.getElementById('qualityScoreText');

  state.subscribe((s) => {
    const isConn = Boolean(s.isBackendConnected);
    if (statusIndicator) {
      statusIndicator.classList.toggle('is-disconnected', !isConn);
    }
    if (ociStatusText) {
      ociStatusText.textContent = isConn
        ? 'Conectado al servidor (FastAPI)'
        : 'Desconectado del servidor (FastAPI)';
    }

    const doc = s.currentDocument;
    if (qualityScoreText) {
      qualityScoreText.textContent = doc
        ? `Capacitación: ${doc.title}`
        : 'Explorando La Biblioteca';
    }
  });
}

function setupBackendBadge() {
  const badge = document.querySelector('.header-connection-badge');
  if (!badge) return;
  const badgeLabel = badge.querySelector('span:not(.status-dot-pulse)') || badge;

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

  state.subscribe((s) => {
    const isConn = Boolean(s.isBackendConnected);
    badge.classList.toggle('is-disconnected', !isConn);
    if (badgeLabel && badgeLabel !== badge) {
      badgeLabel.textContent = isConn ? 'Backend API' : 'Sin Conexión';
    }
    badge.title = isConn
      ? `Conectado a Backend API: ${CONFIG.API.DEFAULT_BASE_URL} (Clic para cambiar)`
      : `Sin conexión con Backend FastAPI (${CONFIG.API.DEFAULT_BASE_URL}). Clic para configurar URL`;
  });
}
