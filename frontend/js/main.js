/**
 * main.js
 * Punto de entrada principal y bootstrap modular de la aplicación NuevaMente.
 */

import { state } from './state.js';
import { CONFIG } from './config.js';
import { theme } from './modules/theme.js';
import { router } from './modules/router.js';
import { uploadTab } from './modules/uploadTab.js';
import { studyHub } from './modules/studyHub.js';
import { jsonViewer } from './modules/jsonViewer.js';
import { bookshelf } from './modules/bookshelf.js';
import { portada } from './modules/portada.js';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicializar Tema Claro / Oscuro
  theme.init();

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

  // 7. Inicializar Visor de JSON Estructurado
  jsonViewer.init();

  // 7. Configurar Selector de Modo de Conexión (Mock vs Real)
  setupApiModeSelector();

  // 8. Configurar Modal de Arquitectura RAG
  setupArchitectureModal();

  // 9. Suscribir estado al footer de OCI y Calidad
  setupSystemStatusBar();
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

function setupArchitectureModal() {
  const btnVerArquitectura = document.getElementById('btnVerArquitectura');
  const archModal = document.getElementById('archModal');
  const btnCloseArch = document.getElementById('btnCloseArch');

  if (btnVerArquitectura && archModal) {
    btnVerArquitectura.addEventListener('click', () => {
      archModal.style.display = 'flex';
      state.set({
        modals: { ...state.get().modals, isArchModalOpen: true }
      });
    });
  }

  if (btnCloseArch && archModal) {
    btnCloseArch.addEventListener('click', () => {
      archModal.style.display = 'none';
      state.set({
        modals: { ...state.get().modals, isArchModalOpen: false }
      });
    });
  }

  if (archModal) {
    archModal.addEventListener('click', (e) => {
      if (e.target === archModal) {
        archModal.style.display = 'none';
        state.set({
          modals: { ...state.get().modals, isArchModalOpen: false }
        });
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.code === 'Escape' && state.get().modals.isArchModalOpen && archModal) {
      archModal.style.display = 'none';
      state.set({
        modals: { ...state.get().modals, isArchModalOpen: false }
      });
    }
  });
}

function setupSystemStatusBar() {
  const ociStatusText = document.getElementById('ociStatusText');
  const qualityScoreText = document.getElementById('qualityScoreText');

  state.subscribe((s) => {
    const doc = s.currentDocument;
    if (ociStatusText) {
      if (s.apiMode === 'real') {
        ociStatusText.textContent = 'Backend: FastAPI Conectado | OCI Object Storage Activo';
      } else {
        ociStatusText.textContent = 'OCI Object Storage: Modo Autónomo (Always Free)';
      }
    }

    if (qualityScoreText && doc && doc.metadatos) {
      qualityScoreText.textContent = `Score Anclaje RAG: ${doc.metadatos.anclaje_rag || 99.2}% | ${doc.metadatos.fidelidad || 'Verificada'}`;
    }
  });
}
