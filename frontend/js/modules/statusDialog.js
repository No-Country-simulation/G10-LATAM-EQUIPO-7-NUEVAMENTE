/**
 * statusDialog.js
 * Diálogo modal temporal para retroalimentación de estado del backend en NuevaMente:
 * - Notificación de documento procesado con status 'stored' e ID en OCI.
 * - Notificación de errores devueltos por el backend (códigos 400, 404, 413, 415, 422, 502, 500, etc.).
 * - Auto-cierre con temporizador interactivo, barra de progreso y pausa en hover.
 */

export const statusDialog = {
  elements: {},
  timerId: null,
  animFrameId: null,
  remainingMs: 0,
  totalDurationMs: 6500,
  startTime: null,
  isPaused: false,

  init() {
    this.ensureDomElements();
    this.bindEvents();
  },

  ensureDomElements() {
    let overlay = document.getElementById('statusDialogOverlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'statusDialogOverlay';
      overlay.className = 'status-dialog-backdrop';
      overlay.style.display = 'none';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-labelledby', 'statusDialogTitle');

      overlay.innerHTML = `
        <div class="status-dialog-card" id="statusDialogCard">
          <!-- Barra de progreso temporal -->
          <div class="status-timer-bar-track">
            <div class="status-timer-bar-fill" id="statusTimerFill"></div>
          </div>

          <!-- Cabecera -->
          <div class="status-dialog-header">
            <div class="status-header-main">
              <div class="status-icon-bubble" id="statusIconBubble"></div>
              <div class="status-title-group">
                <div class="status-badge-row" id="statusBadgeRow"></div>
                <h3 class="status-dialog-title" id="statusDialogTitle">Notificación del Sistema</h3>
              </div>
            </div>
            <button type="button" class="btn-close-status-dialog" id="btnCloseStatusDialog" title="Cerrar (Esc)">&times;</button>
          </div>

          <!-- Contenido Principal -->
          <div class="status-dialog-body" id="statusDialogBody">
            <p class="status-main-message" id="statusMainMessage"></p>

            <!-- Card de Datos OCI (Éxito STORED) -->
            <div class="status-meta-card" id="statusMetaCard" style="display: none;">
              <div class="status-meta-field">
                <div class="meta-label-row">
                  <span class="meta-label">ID / Objeto en OCI Object Storage:</span>
                  <span class="meta-hint-tag">Oracle Cloud Infrastructure</span>
                </div>
                <div class="meta-copyable-row">
                  <code class="meta-code" id="statusOciId">documents/doc_xxx/original.pdf</code>
                  <button type="button" class="btn-copy-oci" id="btnCopyOciId" title="Copiar ID de OCI">
                    <span id="btnCopyOciText">Copiar</span>
                  </button>
                </div>
              </div>
              <div class="status-meta-grid">
                <div class="status-meta-field">
                  <span class="meta-label">ID Canónico del Documento:</span>
                  <code class="meta-code-sm" id="statusDocId">doc_xxx</code>
                </div>
                <div class="status-meta-field">
                  <span class="meta-label">Archivo Procesado:</span>
                  <span class="meta-val" id="statusFileName">archivo.pdf</span>
                </div>
              </div>
            </div>

            <!-- Card de Errores (Códigos 4xx / 5xx) -->
            <div class="status-error-details" id="statusErrorDetails" style="display: none;">
              <div class="status-error-header-row">
                <span class="meta-label">Detalle técnico devuelto por backend:</span>
                <span class="error-code-chip" id="statusErrorCode">BAD_REQUEST</span>
              </div>
              <div class="error-details-box" id="statusErrorBox"></div>
            </div>

            <!-- Fila de tiempo y estado -->
            <div class="status-timestamp-row">
              <span class="status-timestamp" id="statusTimestamp"></span>
              <span class="status-timer-text" id="statusTimerText"></span>
            </div>
          </div>

          <!-- Pie con acción principal -->
          <div class="status-dialog-footer">
            <button type="button" class="btn-status-confirm" id="btnStatusConfirm">
              Entendido
            </button>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);
    }

    this.elements = {
      overlay: document.getElementById('statusDialogOverlay'),
      card: document.getElementById('statusDialogCard'),
      timerFill: document.getElementById('statusTimerFill'),
      iconBubble: document.getElementById('statusIconBubble'),
      badgeRow: document.getElementById('statusBadgeRow'),
      title: document.getElementById('statusDialogTitle'),
      closeBtn: document.getElementById('btnCloseStatusDialog'),
      confirmBtn: document.getElementById('btnStatusConfirm'),
      mainMessage: document.getElementById('statusMainMessage'),
      metaCard: document.getElementById('statusMetaCard'),
      ociId: document.getElementById('statusOciId'),
      btnCopyOci: document.getElementById('btnCopyOciId'),
      btnCopyOciText: document.getElementById('btnCopyOciText'),
      docId: document.getElementById('statusDocId'),
      fileName: document.getElementById('statusFileName'),
      errorDetails: document.getElementById('statusErrorDetails'),
      errorCode: document.getElementById('statusErrorCode'),
      errorBox: document.getElementById('statusErrorBox'),
      timestamp: document.getElementById('statusTimestamp'),
      timerText: document.getElementById('statusTimerText')
    };
  },

  bindEvents() {
    const { overlay, card, closeBtn, confirmBtn, btnCopyOci } = this.elements;

    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (confirmBtn) confirmBtn.addEventListener('click', () => this.close());

    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) this.close();
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay && overlay.style.display !== 'none') {
        this.close();
      }
    });

    if (card) {
      card.addEventListener('mouseenter', () => this.pauseTimer());
      card.addEventListener('mouseleave', () => this.resumeTimer());
    }

    if (btnCopyOci) {
      btnCopyOci.addEventListener('click', () => {
        const text = this.elements.ociId?.textContent || '';
        if (text) {
          navigator.clipboard.writeText(text).then(() => {
            if (this.elements.btnCopyOciText) {
              const prev = this.elements.btnCopyOciText.textContent;
              this.elements.btnCopyOciText.textContent = '¡Copiado!';
              setTimeout(() => {
                if (this.elements.btnCopyOciText) {
                  this.elements.btnCopyOciText.textContent = prev;
                }
              }, 2000);
            }
          }).catch(() => {
            alert(`ID en OCI: ${text}`);
          });
        }
      });
    }
  },

  /**
   * Muestra el dialog cuando el documento fue procesado y su status es 'stored'
   */
  showStored({
    documentId,
    ociId,
    filename,
    httpStatus = 201,
    duplicate = false,
    status = 'indexed',
    durationMs = 7000
  }) {
    this.ensureDomElements();
    this.clearTimer();

    const {
      overlay, card, iconBubble, badgeRow, title,
      mainMessage, metaCard, ociId: elOciId, docId,
      fileName, errorDetails, timestamp, timerText
    } = this.elements;

    // Reset de estilos de tarjeta
    card.classList.remove('status-card-error');
    card.classList.add('status-card-stored');

    // Icono SVG OCI / Almacenamiento Exitoso
    iconBubble.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25"></path>
        <polyline points="8 16 12 20 16 16"></polyline>
        <line x1="12" y1="12" x2="12" y2="20"></line>
      </svg>
    `;

    // Badges informativos
    const isNew = httpStatus === 201 || !duplicate;
    const resolvedStatusTag = String(status || (isNew ? 'stored' : 'indexed')).toUpperCase();
    badgeRow.innerHTML = `
      <span class="status-badge badge-status-stored">STATUS: ${resolvedStatusTag}</span>
      <span class="status-badge ${isNew ? 'badge-http-201' : 'badge-http-200'}">
        HTTP ${httpStatus}: ${isNew ? 'NUEVO DOCUMENTO' : 'DUPLICADO EXISTENTE'}
      </span>
    `;

    title.textContent = isNew
      ? 'Documento Procesado y Almacenado en OCI'
      : 'Documento Existente Detectado y Vinculado en OCI';

    mainMessage.textContent = isNew
      ? `El archivo "${filename}" fue validado, indexado y almacenado de forma persistente en OCI Object Storage.`
      : `El contenido del archivo "${filename}" ya se encontraba registrado (identificado por SHA-256). Se reutilizó el ID existente en OCI.`;

    // Mostrar sección de metadatos (sin reconstruir oci_object_name inventado, Auditoria.md Sec 2: S4)
    metaCard.style.display = 'flex';
    errorDetails.style.display = 'none';

    const ociFieldContainer = elOciId ? elOciId.closest('.status-meta-field') : null;
    if (ociId) {
      if (ociFieldContainer) ociFieldContainer.style.display = 'block';
      elOciId.textContent = ociId;
    } else {
      if (ociFieldContainer) ociFieldContainer.style.display = 'none';
    }

    docId.textContent = documentId;
    fileName.textContent = filename;

    timestamp.textContent = `Registrado: ${new Date().toLocaleTimeString()}`;
    timerText.textContent = `Auto-cierre en ${(durationMs / 1000).toFixed(0)}s (posar el cursor pausa el tiempo)`;

    this.openOverlay(durationMs);
  },

  /**
   * Muestra el dialog cuando el backend responde con un error HTTP (400, 404, 409, 413, 415, 422, 502, 500)
   */
  showError({
    status = 500,
    code = '',
    message = '',
    details = [],
    filename = '',
    durationMs = 9000
  }) {
    this.ensureDomElements();
    this.clearTimer();

    const {
      overlay, card, iconBubble, badgeRow, title,
      mainMessage, metaCard, errorDetails, errorCode,
      errorBox, timestamp, timerText
    } = this.elements;

    card.classList.remove('status-card-stored');
    card.classList.add('status-card-error');

    // Icono SVG de Error
    iconBubble.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
    `;

    const codeLabel = code || this.getCodeForStatus(status);
    const titleForStatus = this.getTitleForStatus(status);

    const isConnError = status === 0;

    // Renderizado seguro de badges (Auditoria.md Sec 8: Prevención DOM XSS)
    badgeRow.textContent = '';
    const badgeStatus = document.createElement('span');
    badgeStatus.className = 'status-badge badge-http-error';
    badgeStatus.textContent = isConnError ? 'CONEXIÓN / RED' : `HTTP ${status}`;

    const badgeCode = document.createElement('span');
    badgeCode.className = 'status-badge badge-code-error';
    badgeCode.textContent = codeLabel;

    badgeRow.appendChild(badgeStatus);
    badgeRow.appendChild(badgeCode);

    title.textContent = titleForStatus;
    mainMessage.textContent = message || this.getDefaultMessageForStatus(status);

    metaCard.style.display = 'none';
    errorDetails.style.display = 'flex';

    errorCode.textContent = codeLabel;

    // Renderizado 100% seguro de detalles mediante nodos DOM (Auditoria.md Sec 8)
    errorBox.textContent = '';
    let hasDetails = false;

    if (filename) {
      const fileRow = document.createElement('div');
      fileRow.className = 'error-detail-line';
      const strong = document.createElement('strong');
      strong.textContent = 'Archivo: ';
      fileRow.appendChild(strong);
      fileRow.appendChild(document.createTextNode(filename));
      errorBox.appendChild(fileRow);
      hasDetails = true;
    }

    if (Array.isArray(details) && details.length > 0) {
      details.forEach((d) => {
        const row = document.createElement('div');
        row.className = 'error-detail-line';
        if (typeof d === 'string') {
          row.textContent = `• ${d}`;
        } else if (typeof d === 'object' && d !== null) {
          const field = d.field || (Array.isArray(d.loc) ? d.loc.join('.') : '');
          const msg = d.message || d.msg || JSON.stringify(d);
          if (field) {
            const strong = document.createElement('strong');
            strong.textContent = `${field}: `;
            row.appendChild(strong);
          } else {
            row.appendChild(document.createTextNode('• '));
          }
          row.appendChild(document.createTextNode(msg));
        }
        errorBox.appendChild(row);
        hasDetails = true;
      });
    } else if (typeof details === 'string' && details.trim()) {
      const row = document.createElement('div');
      row.className = 'error-detail-line';
      row.textContent = details;
      errorBox.appendChild(row);
      hasDetails = true;
    }

    if (!hasDetails) {
      const emptyRow = document.createElement('div');
      emptyRow.className = 'error-detail-line';
      emptyRow.style.color = 'var(--text-muted)';
      emptyRow.style.fontStyle = 'italic';
      const codeInfo = status === 0 ? 'Fallo de conexión o servidor no disponible.' : `Código de respuesta HTTP ${status}.`;
      emptyRow.textContent = `Sin detalles adicionales del servidor. ${codeInfo}`;
      errorBox.appendChild(emptyRow);
    }

    timestamp.textContent = `Reportado: ${new Date().toLocaleTimeString()}`;
    timerText.textContent = `Auto-cierre en ${(durationMs / 1000).toFixed(0)}s (posar el cursor pausa el tiempo)`;

    this.openOverlay(durationMs);
  },

  openOverlay(durationMs) {
    const { overlay, timerFill } = this.elements;
    overlay.style.display = 'flex';

    this.totalDurationMs = durationMs;
    this.remainingMs = durationMs;
    this.startTime = Date.now();
    this.isPaused = false;

    if (timerFill) {
      timerFill.style.width = '100%';
      timerFill.style.transition = 'none';
    }

    this.startCountdownLoop();
  },

  startCountdownLoop() {
    const tick = () => {
      if (this.isPaused) {
        this.animFrameId = requestAnimationFrame(tick);
        return;
      }

      const elapsed = Date.now() - this.startTime;
      this.remainingMs = Math.max(0, this.totalDurationMs - elapsed);

      const ratio = this.remainingMs / this.totalDurationMs;
      if (this.elements.timerFill) {
        this.elements.timerFill.style.width = `${(ratio * 100).toFixed(1)}%`;
      }

      const secondsLeft = Math.ceil(this.remainingMs / 1000);
      if (this.elements.timerText) {
        this.elements.timerText.textContent = `Auto-cierre en ${secondsLeft}s (posar el cursor pausa el tiempo)`;
      }

      if (this.remainingMs <= 0) {
        this.close();
      } else {
        this.animFrameId = requestAnimationFrame(tick);
      }
    };

    this.animFrameId = requestAnimationFrame(tick);
  },

  pauseTimer() {
    if (this.isPaused) return;
    this.isPaused = true;
    if (this.elements.timerText) {
      this.elements.timerText.textContent = 'Temporizador en pausa (mueve el cursor fuera para reanudar)';
    }
  },

  resumeTimer() {
    if (!this.isPaused) return;
    this.isPaused = false;
    this.startTime = Date.now() - (this.totalDurationMs - this.remainingMs);
  },

  clearTimer() {
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.timerId) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
  },

  close() {
    this.clearTimer();
    const { overlay, card } = this.elements;
    if (!overlay || overlay.style.display === 'none') return;

    if (card) {
      card.style.animation = 'statusPopOut 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards';
      setTimeout(() => {
        overlay.style.display = 'none';
        card.style.animation = '';
      }, 190);
    } else {
      overlay.style.display = 'none';
    }
  },

  getCodeForStatus(status) {
    const map = {
      0: 'CONNECTION_REFUSED',
      400: 'BAD_REQUEST',
      404: 'DOCUMENT_NOT_FOUND',
      408: 'REQUEST_TIMEOUT',
      413: 'FILE_TOO_LARGE',
      415: 'UNSUPPORTED_MEDIA_TYPE',
      422: 'REQUEST_VALIDATION_ERROR',
      502: 'OCI_STORAGE_ERROR',
      500: 'INTERNAL_SERVER_ERROR'
    };
    return map[status] || `HTTP_${status}`;
  },

  getTitleForStatus(status) {
    const map = {
      0: 'Error de Conexión con el Backend',
      400: 'Documento Inválido o Vacío',
      404: 'Documento o Recurso No Encontrado',
      408: 'Tiempo de Espera Agotado (Timeout)',
      413: 'Archivo Demasiado Grande (Máx 10 MB)',
      415: 'Formato de Archivo No Soportado',
      422: 'Error de Validación en la Solicitud',
      502: 'Fallo en OCI Object Storage',
      500: 'Error Interno del Servidor'
    };
    return map[status] || `Error HTTP ${status}`;
  },

  getDefaultMessageForStatus(status) {
    const map = {
      0: 'No se pudo establecer conexión con el backend (FastAPI). Verifica que el servicio esté iniciado y accesible.',
      400: 'El documento enviado es inválido o no contiene datos legibles.',
      404: 'No fue posible localizar el documento con el identificador provisto.',
      408: 'Tiempo de espera agotado al comunicarse con el backend (límite de 120 s).',
      413: 'El documento supera el límite máximo de tamaño de archivo admitido por el sistema.',
      415: 'El tipo MIME o extensión del documento no coincide con los formatos admitidos (PDF, Markdown, TXT).',
      422: 'Uno o más campos enviados en la solicitud no cumplen con el esquema requerido.',
      502: 'No fue posible completar la operación de guardado en Oracle Cloud Infrastructure (OCI).',
      500: 'Se produjo un error no controlado en el servidor backend durante el procesamiento.'
    };
    return map[status] || 'Error en la comunicación con el servidor.';
  }
};
