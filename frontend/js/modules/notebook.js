/**
 * notebook.js
 * Renderizador del Cuaderno Interactivo Dinámico y Universal.
 * Genera portada, páginas de contenido e índice para CUALQUIER temática de documento.
 */

import { state } from '../state.js';
import { router } from './router.js';

export const notebook = {
  elements: {},
  spreads: [],

  init() {
    this.bindElements();
    this.setupListeners();
    this.renderBook();

    // Escuchar cambios de documento para reconstruir el cuaderno
    state.subscribe((s) => {
      // Si cambió el documento o la sección
      if (this.lastRenderedDocId !== s.currentDocument?.id) {
        this.renderBook();
      }
    });
  },

  bindElements() {
    this.elements = {
      viewport: document.getElementById('notebookViewport'),
      spreadsContainer: document.getElementById('notebookSpreadsContainer'),
      bottomDock: document.getElementById('notebookBottomDock'),
      btnPagePrev: document.getElementById('btnPagePrev'),
      btnPageNext: document.getElementById('btnPageNext'),
      turnOverlay: document.getElementById('turnOverlay'),
      spreadIndicator: document.getElementById('bookSpreadIndicator'),
      guideInstruction: document.getElementById('guideInstruction'),
      btnIrPortada: document.getElementById('btnIrPortada')
    };
  },

  setupListeners() {
    if (this.elements.btnPagePrev) {
      this.elements.btnPagePrev.addEventListener('click', () => this.goToPrevPage());
    }

    if (this.elements.btnPageNext) {
      this.elements.btnPageNext.addEventListener('click', () => this.goToNextPage());
    }

    if (this.elements.btnIrPortada) {
      this.elements.btnIrPortada.addEventListener('click', () => this.goToSpread(0));
    }

    // Atajos de teclado para navegación de hojas
    document.addEventListener('keydown', (e) => {
      if (state.get().activeTab !== 'notebook') return;

      if (e.code === 'ArrowRight') {
        e.preventDefault();
        this.goToNextPage();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        this.goToPrevPage();
      }
    });
  },

  /**
   * Genera dinámicamente todos los spreads del cuaderno a partir del documento activo
   */
  renderBook() {
    const doc = state.get().currentDocument;
    if (!this.elements.spreadsContainer) return;

    if (!doc) {
      this.lastRenderedDocId = null;
      this.spreads = [];
      this.elements.spreadsContainer.innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:4rem 2rem; text-align:center; color:var(--text-secondary); width:100%;">
          <h3 style="color:var(--text-main); font-size:1.4rem; margin-bottom:0.5rem;">Panel de Lectura en Espera</h3>
          <p style="max-width:500px; font-size:0.95rem; line-height:1.6; margin-bottom:1.5rem;">
            Aún no abriste ningún recurso. Ve al Catálogo de Capacitaciones para seleccionar uno existente o sube un documento nuevo para generar su panel de lectura interactivo.
          </p>
          <button type="button" class="btn-primary-action" id="btnEmptyGoLibrary">
            <span>Explorar el Catálogo de Capacitaciones</span>
          </button>
        </div>
      `;
      this.elements.spreadsContainer.querySelector('#btnEmptyGoLibrary')?.addEventListener('click', () => {
        router.navigate('library');
      });
      if (this.elements.bottomDock) this.elements.bottomDock.innerHTML = '';
      if (this.elements.spreadIndicator) this.elements.spreadIndicator.textContent = 'Sin documento';
      if (this.elements.guideInstruction) this.elements.guideInstruction.textContent = 'Abre un recurso desde el catálogo.';
      if (this.elements.btnPagePrev) this.elements.btnPagePrev.style.display = 'none';
      if (this.elements.btnPageNext) this.elements.btnPageNext.style.display = 'none';
      if (this.elements.btnIrPortada) this.elements.btnIrPortada.style.display = 'none';
      return;
    }

    this.lastRenderedDocId = doc.id;
    this.spreads = [];
    this.elements.spreadsContainer.innerHTML = '';
    this.elements.bottomDock.innerHTML = '';

    // 1. Crear Spread 0: Portada
    const coverSpread = this.createCoverSpread(doc);
    this.spreads.push({
      id: 'spread_cover',
      title: 'Portada',
      instruction: `Explora el módulo de capacitación estructurado para: ${doc.title}`,
      element: coverSpread
    });
    this.elements.spreadsContainer.appendChild(coverSpread);

    // 2. Crear Spreads de Secciones (emparejadas de 2 en 2 para simular libro abierto)
    const sections = doc.sections || [];
    for (let i = 0; i < sections.length; i += 2) {
      const leftSec = sections[i];
      const rightSec = sections[i + 1] || null;
      const spreadIndex = this.spreads.length;

      const sectionSpread = this.createSectionSpread(leftSec, rightSec, i + 1, i + 2, doc);
      const titleLabel = rightSec ? `Págs ${i + 1}-${i + 2}: Contenido` : `Pág ${i + 1}: Contenido`;

      this.spreads.push({
        id: `spread_sec_${i}`,
        title: titleLabel,
        instruction: 'Haz clic en "Capacitar en esta Sección" en cualquier módulo para acceder a las Flashcards, Quiz y Video.',
        element: sectionSpread
      });
      this.elements.spreadsContainer.appendChild(sectionSpread);
    }

    // 3. Crear Spread Final: Índice Interactivo
    const indexSpread = this.createIndexSpread(doc);
    this.spreads.push({
      id: 'spread_index',
      title: 'Índice General',
      instruction: 'Haz clic en cualquier sección del índice para ir directamente a sus páginas de capacitación.',
      element: indexSpread
    });
    this.elements.spreadsContainer.appendChild(indexSpread);

    // 4. Construir Dock Inferior de Páginas
    this.renderBottomDock();

    // 5. Mostrar la portada inicial o spread actual
    const targetSpread = state.get().notebook.currentSpreadIndex || 0;
    this.updateSpreadDisplay(targetSpread);
  },

  createCoverSpread(doc) {
    const spread = document.createElement('div');
    spread.className = 'notebook-spread notebook-cover-layout';
    spread.id = 'viewCoverDynamic';

    const meta = doc.metadatos || {};
    const lm = doc.learning_metadata || {};
    const tiempoEstudio = typeof lm.estimated_time_minutes === 'number'
      ? `${lm.estimated_time_minutes} min`
      : (typeof doc.estimated_time_minutes === 'number' ? `${doc.estimated_time_minutes} min` : (meta.tiempo_estudio || '8 min'));

    const prereqs = Array.isArray(lm.prerequisites) && lm.prerequisites.length > 0
      ? lm.prerequisites
      : (Array.isArray(doc.prerequisites) ? doc.prerequisites : []);

    spread.innerHTML = `
      <span class="cover-emboss-badge"></span>
      <h2 class="cover-doc-title"></h2>
      <p class="cover-doc-description"></p>
      
      <div class="cover-meta-grid">
        <div class="cover-meta-item">Nivel: <strong class="meta-level"></strong></div>
        <div class="cover-meta-item">Tiempo estimado: <strong class="meta-time"></strong></div>
        <div class="cover-meta-item">Archivo: <strong class="meta-file"></strong></div>
      </div>

      <button type="button" class="btn-open-notebook" id="btnOpenDynamicNotebook">
        <span>Abrir Módulo de Capacitación</span>
      </button>
    `;

    spread.querySelector('.cover-emboss-badge').textContent = doc.discipline || 'Documentación Corporativa';
    spread.querySelector('.cover-doc-title').textContent = doc.title || 'Módulo Corporativo';
    spread.querySelector('.cover-doc-description').textContent = doc.description || doc.summary || 'Programa formativo interactivo.';
    spread.querySelector('.meta-level').textContent = meta.perfil || 'Operativo';
    spread.querySelector('.meta-time').textContent = tiempoEstudio;
    spread.querySelector('.meta-file').textContent = doc.filename || '';

    if (prereqs.length > 0) {
      const metaGrid = spread.querySelector('.cover-meta-grid');
      const prereqsItem = document.createElement('div');
      prereqsItem.className = 'cover-meta-item';
      prereqsItem.style.gridColumn = '1 / -1';
      prereqsItem.textContent = 'Prerrequisitos: ';
      const strong = document.createElement('strong');
      strong.textContent = prereqs.join(', ');
      prereqsItem.appendChild(strong);
      metaGrid.appendChild(prereqsItem);
    }

    spread.querySelector('#btnOpenDynamicNotebook')?.addEventListener('click', () => {
      this.goToSpread(1);
    });

    return spread;
  },

  createSectionSpread(leftSec, rightSec, leftNum, rightNum, doc) {
    const spread = document.createElement('div');
    spread.className = 'notebook-spread spread-two-pages';

    const renderHalf = (sec, pageNum) => {
      if (!sec) {
        return `
          <div class="page-half">
            <div class="page-header-row">
              <span class="page-chapter-badge">Notas de Capacitación</span>
              <span class="page-number-label">Pág. ${pageNum}</span>
            </div>
            <div class="page-body-content" style="justify-content: center; align-items: center; opacity: 0.6;">
              <p>Espacio reservado para anotaciones del colaborador y síntesis operativa.</p>
            </div>
            <div class="page-footer-actions">
              <span class="page-number-label">—</span>
            </div>
          </div>
        `;
      }

      const chipsHtml = (sec.key_concepts || []).map(c => `<span class="concept-chip">${c}</span>`).join('');
      return `
        <div class="page-half" data-sec-id="${sec.id}">
          <div class="page-header-row">
            <div>
              <span class="page-chapter-badge">Módulo ${pageNum}</span>
              <h4 class="page-topic-title">${sec.title}</h4>
            </div>
            <span class="page-number-label">Pág. ${pageNum}</span>
          </div>

          <div class="page-body-content">
            <p>${sec.summary}</p>
            <div class="page-key-concepts-box">
              <h5>Competencias y Puntos Clave:</h5>
              <div class="concept-chips">${chipsHtml}</div>
            </div>
          </div>

          <div class="page-footer-actions">
            <button type="button" class="btn-study-badge" data-study-section="${sec.id}">
              <span>Capacitar en esta Sección</span>
            </button>
            <span class="page-number-label">${doc.discipline}</span>
          </div>
        </div>
      `;
    };

    spread.innerHTML = renderHalf(leftSec, leftNum) + renderHalf(rightSec, rightNum);

    // Event listeners para los botones de estudio en esta página
    spread.querySelectorAll('[data-study-section]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const secId = btn.getAttribute('data-study-section');
        this.openSectionStudy(secId);
      });
    });

    return spread;
  },

  createIndexSpread(doc) {
    const spread = document.createElement('div');
    spread.className = 'notebook-spread index-page-layout';

    const topicsHtml = (doc.sections || []).map((sec, idx) => {
      // Mapear el índice de la sección al spread correspondiente (spread 1 contiene sec 0 y 1, etc.)
      const targetSpreadIndex = Math.floor(idx / 2) + 1;
      return `
        <div class="index-topic-card" data-jump-spread="${targetSpreadIndex}">
          <strong>${idx + 1}. ${sec.title}</strong>
          <span>${sec.key_concepts?.slice(0, 3).join(', ') || 'Conceptos clave'}</span>
        </div>
      `;
    }).join('');

    spread.innerHTML = `
      <div class="page-header-row">
        <h3 class="index-page-title">Índice Temático del Documento</h3>
        <span class="badge-pill badge-gold">${doc.sections?.length || 0} Secciones</span>
      </div>
      <p style="color: var(--text-secondary); font-size: 0.92rem;">
        Haz clic en cualquier sección para saltar directamente a sus páginas en el panel de lectura.
      </p>
      <div class="index-topics-grid">
        ${topicsHtml}
      </div>
    `;

    spread.querySelectorAll('[data-jump-spread]').forEach(card => {
      card.addEventListener('click', () => {
        const sIndex = parseInt(card.getAttribute('data-jump-spread'), 10);
        this.goToSpread(sIndex);
      });
    });

    return spread;
  },

  renderBottomDock() {
    const { bottomDock } = this.elements;
    if (!bottomDock) return;

    this.spreads.forEach((spread, index) => {
      const btn = document.createElement('button');
      btn.className = 'dock-page-btn';
      btn.textContent = spread.title;
      btn.setAttribute('data-spread-index', index);

      btn.addEventListener('click', () => {
        this.goToSpread(index);
      });

      bottomDock.appendChild(btn);
    });
  },

  /**
   * Navega suavemente al spread objetivo con la animación de página (animacion3d.jpg)
   */
  goToSpread(targetIndex) {
    if (targetIndex < 0 || targetIndex >= this.spreads.length) return;
    const currentState = state.get().notebook;
    if (currentState.isTurningPage || targetIndex === currentState.currentSpreadIndex) return;

    state.set({
      notebook: {
        ...currentState,
        isTurningPage: true
      }
    });

    // Mostrar overlay de animación 3D
    if (this.elements.turnOverlay) {
      this.elements.turnOverlay.classList.add('turning');
    }

    setTimeout(() => {
      this.updateSpreadDisplay(targetIndex);
      if (this.elements.turnOverlay) {
        this.elements.turnOverlay.classList.remove('turning');
      }
      state.set({
        notebook: {
          ...state.get().notebook,
          currentSpreadIndex: targetIndex,
          isTurningPage: false
        }
      });
    }, 300);
  },

  goToNextPage() {
    const current = state.get().notebook.currentSpreadIndex;
    if (current < this.spreads.length - 1) {
      this.goToSpread(current + 1);
    }
  },

  goToPrevPage() {
    const current = state.get().notebook.currentSpreadIndex;
    if (current > 0) {
      this.goToSpread(current - 1);
    }
  },

  updateSpreadDisplay(index) {
    if (!this.spreads[index]) return;

    // Mostrar/ocultar elementos
    this.spreads.forEach((s, idx) => {
      if (idx === index) {
        s.element.classList.add('active');
      } else {
        s.element.classList.remove('active');
      }
    });

    const activeSpread = this.spreads[index];
    if (this.elements.spreadIndicator) {
      this.elements.spreadIndicator.textContent = activeSpread.title;
    }
    if (this.elements.guideInstruction) {
      this.elements.guideInstruction.textContent = activeSpread.instruction;
    }

    // Flechas laterales
    if (this.elements.btnPagePrev) {
      this.elements.btnPagePrev.style.display = index === 0 ? 'none' : 'flex';
    }
    if (this.elements.btnPageNext) {
      this.elements.btnPageNext.style.display = index === this.spreads.length - 1 ? 'none' : 'flex';
    }
    if (this.elements.btnIrPortada) {
      this.elements.btnIrPortada.style.display = index === 0 ? 'none' : 'inline-flex';
    }

    // Sincronizar dock inferior
    const dockButtons = this.elements.bottomDock?.querySelectorAll('.dock-page-btn');
    dockButtons?.forEach((btn, idx) => {
      if (idx === index) {
        btn.classList.add('active');
        btn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      } else {
        btn.classList.remove('active');
      }
    });
  },

  openSectionStudy(sectionId) {
    state.set({
      studyHub: {
        ...state.get().studyHub,
        activeSectionId: sectionId,
        activeFormat: 'flashcards',
        currentCardIndex: 0,
        isFlipped: false
      }
    });
    router.navigate('study');
  }
};
