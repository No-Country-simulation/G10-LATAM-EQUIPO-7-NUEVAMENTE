/**
 * notifications.js
 * Sistema de Notificaciones y Feedback UX (Toasts / Alertas Glassmorphism)
 * Soporta estados: éxito (201), advertencia/duplicado (200), errores (400, 404, 413, 415, 422, 502, 500)
 */

let container = null;

function getOrCreateContainer() {
  if (container && document.body.contains(container)) {
    return container;
  }
  container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', 'Notificaciones del sistema');
    document.body.appendChild(container);
  }
  return container;
}

/**
 * Muestra una notificación toast interactiva y accesible
 * @param {Object} options
 * @param {'success'|'warning'|'error'|'info'} options.type
 * @param {string} options.title
 * @param {string} options.message
 * @param {number} [options.duration=6000] - Tiempo en ms antes de auto-cerrarse (0 = permanente)
 * @param {string} [options.actionText]
 * @param {Function} [options.onAction]
 * @returns {HTMLElement} Elemento del toast
 */
export function showToast({
  type = 'info',
  title = '',
  message = '',
  duration = 6000,
  actionText = null,
  onAction = null
}) {
  const toastContainer = getOrCreateContainer();

  const toast = document.createElement('div');
  toast.className = `toast-item toast-${type}`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');

  const iconEl = document.createElement('div');
  iconEl.className = 'toast-icon';

  const bodyEl = document.createElement('div');
  bodyEl.className = 'toast-body';

  if (title) {
    const titleEl = document.createElement('div');
    titleEl.className = 'toast-title';
    titleEl.textContent = title;
    bodyEl.appendChild(titleEl);
  }

  if (message) {
    const msgEl = document.createElement('div');
    msgEl.className = 'toast-message';
    msgEl.textContent = message;
    bodyEl.appendChild(msgEl);
  }

  if (actionText && typeof onAction === 'function') {
    const actionBtn = document.createElement('button');
    actionBtn.type = 'button';
    actionBtn.className = 'toast-action-btn';
    actionBtn.textContent = actionText;
    actionBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      onAction();
      dismissToast(toast);
    });
    bodyEl.appendChild(actionBtn);
  }

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'toast-close-btn';
  closeBtn.innerHTML = '&times;';
  closeBtn.setAttribute('aria-label', 'Cerrar notificación');
  closeBtn.addEventListener('click', () => dismissToast(toast));

  toast.appendChild(iconEl);
  toast.appendChild(bodyEl);
  toast.appendChild(closeBtn);

  toastContainer.appendChild(toast);

  // Forzar reflow para animación CSS
  requestAnimationFrame(() => {
    toast.classList.add('toast-visible');
  });

  // Temporizador de auto-cierre si duration > 0
  let timeoutId = null;
  if (duration > 0) {
    timeoutId = setTimeout(() => {
      dismissToast(toast);
    }, duration);

    // Pausar auto-cierre en hover
    toast.addEventListener('mouseenter', () => {
      if (timeoutId) clearTimeout(timeoutId);
    });
    toast.addEventListener('mouseleave', () => {
      timeoutId = setTimeout(() => dismissToast(toast), 2500);
    });
  }

  return toast;
}

export function dismissToast(toast) {
  if (!toast || !toast.parentNode) return;
  toast.classList.remove('toast-visible');
  toast.classList.add('toast-hiding');
  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, 300);
}

/**
 * Helpers específicos para tipos frecuentes
 */
export function notifySuccess(title, message, options = {}) {
  return showToast({ type: 'success', title, message, ...options });
}

export function notifyWarning(title, message, options = {}) {
  return showToast({ type: 'warning', title, message, ...options });
}

export function notifyError(title, message, options = {}) {
  // Errores duran 8s por defecto para permitir lectura clara
  return showToast({ type: 'error', title, message, duration: 8000, ...options });
}

export function notifyInfo(title, message, options = {}) {
  return showToast({ type: 'info', title, message, ...options });
}
