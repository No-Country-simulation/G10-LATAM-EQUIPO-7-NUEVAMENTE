/**
 * backendStatus.js
 * Monitor en tiempo real del estado de conexión con la API de FastAPI.
 * Mantiene sincronizados el badge del topbar, la tarjeta del catálogo y la barra de estado.
 */

import { CONFIG } from '../config.js';
import { apiClient } from '../api/apiClient.js';

export const backendStatus = {
  isChecking: false,
  isOnline: false,
  timer: null,

  init() {
    this.bindElements();
    this.check();
    // Verificación periódica cada 12 segundos
    this.timer = setInterval(() => this.check(false), 12000);
  },

  bindElements() {
    this.badge = document.getElementById('headerBackendBadge');
    this.badgeText = document.getElementById('headerBackendText');
    this.badgeDot = document.getElementById('headerBackendDot');

    this.cardVal = document.getElementById('metricBackendVal');
    this.cardText = document.getElementById('metricBackendText');
    this.cardDot = document.getElementById('metricBackendDot');

    this.footerDot = document.getElementById('footerBackendDot');
    this.footerText = document.getElementById('ociStatusText');

    // Permitir clic para reverificar manualmente
    if (this.badge) {
      this.badge.addEventListener('click', () => this.check(true));
    }
    const metricCard = document.getElementById('metricBackendCard');
    if (metricCard) {
      metricCard.addEventListener('click', () => this.check(true));
    }
  },

  /**
   * Ejecuta el health-check contra FastAPI
   * @param {boolean} isManual Indica si fue disparado manualmente por clic del usuario
   */
  async check(isManual = false) {
    if (this.isChecking) return;
    this.isChecking = true;

    if (isManual) {
      this.setUIState('checking');
    }

    try {
      const ok = await apiClient.checkHealth();
      this.isOnline = ok;
      this.setUIState(ok ? 'online' : 'offline');
    } catch {
      this.isOnline = false;
      this.setUIState('offline');
    } finally {
      this.isChecking = false;
    }
  },

  /**
   * Actualiza los elementos del DOM según el estado de salud
   * @param {'online' | 'offline' | 'checking'} status
   */
  setUIState(status) {
    const isOnline = status === 'online';
    const isChecking = status === 'checking';

    // 1. Badge en la Cabecera Superior
    if (this.badge) {
      this.badge.classList.remove('status-online', 'status-offline', 'status-checking');
      this.badge.classList.add(`status-${status}`);
      this.badge.title = isOnline
        ? `Backend FastAPI activo en ${CONFIG.API.DEFAULT_BASE_URL} (Clic para reverificar)`
        : `Sin conexión con ${CONFIG.API.DEFAULT_BASE_URL} (Clic para reintentar)`;
    }

    if (this.badgeText) {
      this.badgeText.textContent = isOnline
        ? 'FastAPI Conectado'
        : (isChecking ? 'Verificando Backend...' : 'FastAPI Desconectado');
    }

    // 2. Tarjeta en el Catálogo de la Biblioteca
    if (this.cardVal) {
      this.cardVal.classList.remove('status-online', 'status-offline', 'status-checking');
      this.cardVal.classList.add(`status-${status}`);
    }

    if (this.cardText) {
      this.cardText.textContent = isOnline ? 'Online' : (isChecking ? 'Verificando...' : 'Offline');
      this.cardText.style.color = isOnline ? '#34d399' : (isChecking ? '#fbbf24' : '#f87171');
    }

    if (this.cardDot) {
      this.cardDot.style.background = isOnline ? '#10b981' : (isChecking ? '#f59e0b' : '#ef4444');
      this.cardDot.style.boxShadow = isOnline ? '0 0 8px #10b981' : 'none';
      this.cardDot.style.animation = isOnline ? 'pulseDotGreen 2s infinite ease-in-out' : 'none';
    }

    // 3. Barra de Estado Inferior (Footer)
    if (this.footerDot) {
      this.footerDot.style.background = isOnline ? '#10b981' : (isChecking ? '#f59e0b' : '#ef4444');
      this.footerDot.style.boxShadow = isOnline ? '0 0 8px #10b981' : 'none';
    }

    if (this.footerText) {
      this.footerText.textContent = isOnline
        ? `Conectado a Backend API (${CONFIG.API.DEFAULT_BASE_URL})`
        : `Backend Desconectado (${CONFIG.API.DEFAULT_BASE_URL})`;
      this.footerText.style.color = isOnline ? '#a1a1aa' : '#f87171';
    }
  }
};
