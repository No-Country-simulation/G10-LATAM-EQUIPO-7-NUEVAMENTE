/**
 * bookshelf.js
 * Controlador del Gran Librero Interactivo de NuevaMente y del Cuaderno Abierto.
 */

import { state } from '../state.js';
import { getRandomSpineColor } from '../config.js';
import { apiClient } from '../api/apiClient.js';
import { router } from './router.js';
import { statusDialog } from './statusDialog.js';
import { notifyError, notifyWarning } from './notifications.js';
import { toFriendlyError } from '../utils/friendlyError.js';

export const bookshelf = {
  elements: {},
  currentSelectedBook: null,
  booksFromBackend: [],
  allBooks: [],
  currentSearchQuery: '',
  activeCategory: null,
  isLoadingBackend: false,

  async init() {
    this.bindElements();
    this.setupToggleInteractiveMode();
    this.setupSearchEvents();
    this.renderShelf();
    this.setupModalEvents();

    // Tarea 6: Solicitar los libros existentes al Backend (GET /api/v1/documents)
    await this.fetchBackendBooks();

    // Re-renderizar si cambia el documento cargado o si el usuario navega a La Biblioteca
    state.subscribe((s) => {
      if (s.activeTab === 'library' || s.currentDocument) {
        this.renderShelf();
      }
      this.updateBackendMetric(s.isBackendConnected);
    });
  },

  /**
   * Consulta los documentos persistidos en el Backend (GET /documents)
   * Diagrama C - Flujo de Consulta desde la Biblioteca
   */
  async fetchBackendBooks() {
    try {
      this.isLoadingBackend = true;
      this.showShelfLoading(true);

      const docs = await apiClient.getDocuments();

      if (Array.isArray(docs) && docs.length > 0) {
        this.booksFromBackend = docs.map((doc, idx) => {
          const rawTitle = doc.title || doc.filename || doc.original_filename || `Documento ${idx + 1}`;
          const cleanTitle = rawTitle.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ').trim();
          const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
          const docId = doc.document_id || doc.id || `doc_${idx}`;
          const ext = (doc.filename || doc.original_filename || 'pdf').split('.').pop().toUpperCase();
          const discipline = doc.discipline || this.inferDiscipline(cleanTitle);

          return {
            id: docId,
            title: formattedTitle,
            filename: doc.filename || doc.original_filename || `${cleanTitle}.pdf`,
            discipline: discipline,
            spineColor: doc.spineColor || getRandomSpineColor(),
            description: doc.summary || doc.description || `Documento persistido en Backend y OCI Object Storage.`,
            filesize: doc.size_bytes ? `${(doc.size_bytes / (1024 * 1024)).toFixed(1)} MB` : '1.5 MB',
            status: doc.status || 'stored',
            metadatos: {
              document_id: docId,
              tiempo_estudio: typeof doc.estimated_time_minutes === 'number'
                ? `${doc.estimated_time_minutes} min`
                : (doc.estimated_time || '8 min'),
              perfil: doc.target_profile || doc.profile || 'intermediate',
              formato: ext
            },
            key_concepts: Array.isArray(doc.key_concepts) ? doc.key_concepts : [],
            prerequisites: Array.isArray(doc.prerequisites) ? doc.prerequisites : [],
            sections: doc.sections || [
              {
                id: `sec_${docId}`,
                title: formattedTitle,
                summary: doc.summary || `Contenido de ${formattedTitle} analizado por NuevaMente.`,
                key_concepts: Array.isArray(doc.key_concepts) && doc.key_concepts.length > 0
                  ? doc.key_concepts
                  : [discipline, 'Concepto Clave', 'Persistencia OCI']
              }
            ]
          };
        });
        console.log(`[Bookshelf] ${this.booksFromBackend.length} libros recuperados desde Backend API.`);
      } else {
        this.booksFromBackend = [];
      }
    } catch (err) {
      console.warn('[Bookshelf] Backend GET /documents no disponible aún o sin conexión:', err.message);
      this.booksFromBackend = [];
      const friendly = toFriendlyError(err);
      if (friendly.status >= 500 || friendly.status === 502) {
        statusDialog.showError({
          status: friendly.status,
          code: friendly.code,
          message: friendly.message,
          details: err.details || ['GET /api/v1/documents', friendly.message]
        });
      }
      notifyWarning(
        friendly.title,
        friendly.message
      );
    } finally {
      this.isLoadingBackend = false;
      this.showShelfLoading(false);
      this.renderShelf();
    }
  },

  showShelfLoading(isLoading) {
    const subtitle = document.querySelector('.library-hero-subtitle');
    if (!subtitle) return;
    if (isLoading) {
      subtitle.setAttribute('data-original-text', subtitle.textContent);
      subtitle.innerHTML = '<span class="status-dot-pulse" style="display:inline-block; margin-right:6px;"></span> Sincronizando recursos con el servidor...';
    } else {
      const orig = subtitle.getAttribute('data-original-text');
      if (orig) subtitle.textContent = orig;
    }
  },

  inferDiscipline(title) {
    const lower = (title || '').toLowerCase();
    if (lower.includes('cloud') || lower.includes('software') || lower.includes('codigo') || lower.includes('programacion') || lower.includes('arquitectura') || lower.includes('microservicio') || lower.includes('api')) return 'Ingeniería de Software';
    if (lower.includes('med') || lower.includes('neuro') || lower.includes('salud') || lower.includes('bio') || lower.includes('farmac') || lower.includes('clinica')) return 'Ciencias Médicas & Biología';
    if (lower.includes('ley') || lower.includes('derecho') || lower.includes('legal') || lower.includes('constitucion') || lower.includes('norma') || lower.includes('jurid')) return 'Ciencias Jurídicas & Derecho';
    if (lower.includes('negocio') || lower.includes('econom') || lower.includes('finanz') || lower.includes('market') || lower.includes('empresa')) return 'Economía & Negocios';
    if (lower.includes('data') || lower.includes('ia') || lower.includes('inteligencia') || lower.includes('machine') || lower.includes('learning')) return 'Inteligencia Artificial';
    return 'Ciencias Generales';
  },

  bindElements() {
    this.elements = {
      shelfRow1: document.getElementById('shelfRow1'),
      shelfRow2: document.getElementById('shelfRow2'),
      openBookOverlay: document.getElementById('openBookOverlay'),
      btnCloseOverlay: document.getElementById('btnCloseNotebookOverlay'),
      btnStartStudying: document.getElementById('btnStartStudying'),

      // Campos de la Hoja Izquierda
      openedBadge: document.getElementById('openedDocBadge'),
      openedTitle: document.getElementById('openedDocTitle'),
      openedSummary: document.getElementById('openedDocSummary'),
      openedTime: document.getElementById('openedDocTime'),
      openedSections: document.getElementById('openedDocSections'),
      openedLevel: document.getElementById('openedDocLevel'),
      openedChips: document.getElementById('openedDocChips'),

      // Opciones de Estudio de la Hoja Derecha
      studyChoiceCards: document.querySelectorAll('.btn-study-choice-card'),

      // Botón de Carga Rápida en el Hero de la Biblioteca
      btnHeroUploadQuick: document.getElementById('btnHeroUploadQuick'),

      // Conmutadores de Modo Interactivo
      btnToggleInteractive: document.getElementById('btnToggleInteractive'),
      btnReturnToListMode: document.getElementById('btnReturnToListMode'),
      btnCatalogUploadAction: document.getElementById('btnCatalogUploadAction'),

      // Elementos del Catálogo en Modo Lista
      docListEl: document.getElementById('cosmicDocList'),
      metricDocCount: document.getElementById('metricDocCount'),
      metricBackendCard: document.getElementById('metricBackendCard'),
      metricBackendVal: document.getElementById('metricBackendVal'),
      metricBackendText: document.getElementById('metricBackendText'),
      metricBackendDot: document.getElementById('metricBackendDot'),
      searchList: document.getElementById('searchDocList'),
      clearList: document.getElementById('btnClearSearchList'),
      searchCountList: document.getElementById('searchCountList'),
      search3D: document.getElementById('searchDoc3D'),
      clear3D: document.getElementById('btnClearSearch3D'),
      searchCount3D: document.getElementById('searchCount3D'),
      chips: document.querySelectorAll('.cosmic-chip')
    };
  },

  renderShelf() {
    const { shelfRow1, shelfRow2 } = this.elements;
    if (!shelfRow1) return;

    shelfRow1.innerHTML = '<div class="shelf-plank"></div>';
    if (shelfRow2) {
      shelfRow2.innerHTML = '<div class="shelf-plank"></div>';
      shelfRow2.style.display = 'flex';
    }

    // Unificar libros reales sin duplicados:
    // 1. Libros recuperados desde Backend (GET /documents)
    // 2. Libros subidos en cliente (state.customBooks)
    const booksMap = new Map();
    const customBooks = state.get().customBooks || [];

    // Priorizar customBooks subidos por el usuario en esta u otras sesiones
    customBooks.forEach((cDoc) => {
      booksMap.set(cDoc.id, {
        ...cDoc,
        spineColor: cDoc.spineColor || getRandomSpineColor()
      });
    });

    // Agregar libros provenientes del Backend si no están ya en el mapa
    (this.booksFromBackend || []).forEach(b => {
      if (!booksMap.has(b.id)) {
        booksMap.set(b.id, b);
      }
    });

    const currentDoc = state.get().currentDocument;
    if (currentDoc && !booksMap.has(currentDoc.id)) {
      booksMap.set(currentDoc.id, {
        ...currentDoc,
        spineColor: currentDoc.spineColor || getRandomSpineColor()
      });
    }

    const books = Array.from(booksMap.values());
    this.allBooks = books;

    // Actualizar KPIs de la cabecera del catálogo
    const { metricDocCount, searchCountList } = this.elements;
    if (metricDocCount) {
      metricDocCount.textContent = books.length;
    }
    if (searchCountList) {
      searchCountList.textContent = `${books.length} documentos`;
    }
    this.updateBackendMetric(state.get().isBackendConnected);

    // 1. Renderizar Catálogo en Lista (Modo por Defecto)
    this.renderCatalogList(books);

    // 2. Renderizar Estantería 3D (Modo Interactivo)
    if (books.length === 0) {
      const emptyContainer = document.createElement('div');
      emptyContainer.className = 'shelf-empty-state';
      emptyContainer.innerHTML = `
        <div class="empty-shelf-card">
          <h4>Tu Catálogo de Capacitaciones está Listo</h4>
          <p>Aún no hay documentos en el servidor. Sube tu primer archivo PDF, Markdown o TXT para comenzar.</p>
          <button type="button" class="btn-primary-action btn-empty-upload" id="btnEmptyUpload">
            <span>+ Subir Mi Primer Documento</span>
          </button>
        </div>
      `;

      emptyContainer.querySelector('#btnEmptyUpload')?.addEventListener('click', () => {
        router.navigate('upload');
      });

      shelfRow1.appendChild(emptyContainer);
      shelfRow1.appendChild(this.createUploadSlotSpine());

      if (shelfRow2) {
        shelfRow2.style.display = 'none';
      }
      return;
    }

    // Dividimos los libros entre el estante superior (Row 1) y el inferior (Row 2)
    const mid = Math.ceil(books.length / 2);
    const row1Books = books.slice(0, mid);
    const row2Books = books.slice(mid);

    row1Books.forEach(book => {
      shelfRow1.appendChild(this.createBookSpine(book));
    });

    if (shelfRow2) {
      shelfRow2.style.display = 'flex';
      row2Books.forEach(book => {
        shelfRow2.appendChild(this.createBookSpine(book));
      });

      // Agregar el Tomo Especial: "+ Subir Nuevo Documento" al final del estante
      shelfRow2.appendChild(this.createUploadSlotSpine());
    } else {
      shelfRow1.appendChild(this.createUploadSlotSpine());
    }
  },

  /**
   * Conmuta entre el Modo Lista (por defecto) y el Modo Interactivo (Estantería 3D)
   */
  setupToggleInteractiveMode() {
    const { btnToggleInteractive, btnReturnToListMode, btnCatalogUploadAction, metricBackendCard } = this.elements;

    if (btnToggleInteractive) {
      btnToggleInteractive.addEventListener('click', (e) => {
        e.preventDefault();
        const isInteractive = document.body.classList.toggle('interactive-mode-active');
        btnToggleInteractive.innerHTML = isInteractive ? '<span>Modo Lista</span>' : '<span>Modo Interactivo</span>';
        btnToggleInteractive.title = isInteractive ? 'Cambiar a vista de lista' : 'Cambiar a estantería interactiva 3D';

        // Asegurarse de navegar a la pestaña de biblioteca
        if (state.get().activeTab !== 'library') {
          router.navigate('library');
        }
      });
    }

    if (btnReturnToListMode) {
      btnReturnToListMode.addEventListener('click', (e) => {
        e.preventDefault();
        document.body.classList.remove('interactive-mode-active');
        if (btnToggleInteractive) {
          btnToggleInteractive.innerHTML = '<span>Modo Interactivo</span>';
          btnToggleInteractive.title = 'Cambiar a estantería interactiva 3D';
        }
      });
    }

    if (btnCatalogUploadAction) {
      btnCatalogUploadAction.addEventListener('click', (e) => {
        e.preventDefault();
        router.navigate('upload');
      });
    }

    if (metricBackendCard) {
      metricBackendCard.addEventListener('click', () => {
        apiClient.checkHealth();
      });
    }
  },

  /**
   * Configura eventos de búsqueda y filtros en el Catálogo en Modo Lista y Estantería 3D
   */
  setupSearchEvents() {
    const { searchList, clearList, search3D, clear3D, chips } = this.elements;

    const handleSearchInput = (value) => {
      this.currentSearchQuery = value.trim();

      if (searchList && searchList.value !== value) searchList.value = value;
      if (search3D && search3D.value !== value) search3D.value = value;

      if (clearList) clearList.style.display = value ? 'flex' : 'none';
      if (clear3D) clear3D.style.display = value ? 'flex' : 'none';

      this.filterBooks();
    };

    if (searchList) {
      searchList.addEventListener('input', (e) => handleSearchInput(e.target.value));
    }
    if (search3D) {
      search3D.addEventListener('input', (e) => handleSearchInput(e.target.value));
    }

    if (clearList) {
      clearList.addEventListener('click', () => {
        handleSearchInput('');
        if (searchList) searchList.focus();
      });
    }
    if (clear3D) {
      clear3D.addEventListener('click', () => {
        handleSearchInput('');
        if (search3D) search3D.focus();
      });
    }

    if (chips && chips.length > 0) {
      chips.forEach(chip => {
        chip.addEventListener('click', () => {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          const text = chip.textContent.trim().toLowerCase();
          if (text.startsWith('todos')) {
            this.activeCategory = null;
          } else if (text.includes('tecnología') || text.includes('cloud') || text.includes('software')) {
            this.activeCategory = 'tecnología';
          } else if (text.includes('legal') || text.includes('compliance') || text.includes('derecho')) {
            this.activeCategory = 'legal';
          } else if (text.includes('operaciones') || text.includes('negocios') || text.includes('finanzas')) {
            this.activeCategory = 'operaciones';
          } else if (text.includes('rrhh') || text.includes('gestión') || text.includes('humano')) {
            this.activeCategory = 'rrhh';
          } else {
            this.activeCategory = null;
          }
          this.filterBooks();
        });
      });
    }
  },

  /**
   * Filtra los documentos por búsqueda y categoría tanto en lista como en la estantería 3D
   */
  filterBooks() {
    const q = (this.currentSearchQuery || '').toLowerCase();
    const cat = this.activeCategory;
    const all = this.allBooks || [];

    const matchesCategory = (book) => {
      if (!cat) return true;
      const disc = (book.discipline || '').toLowerCase();
      if (cat === 'tecnología') {
        return disc.includes('software') || disc.includes('cloud') || disc.includes('ingeniería') || disc.includes('inteligencia') || disc.includes('datos') || disc.includes('dev');
      }
      if (cat === 'legal') {
        return disc.includes('derecho') || disc.includes('leyes') || disc.includes('jurídicas') || disc.includes('compliance') || disc.includes('ciberseguridad');
      }
      if (cat === 'operaciones') {
        return disc.includes('economía') || disc.includes('negocios') || disc.includes('finanzas') || disc.includes('operaciones');
      }
      if (cat === 'rrhh') {
        return disc.includes('humanidades') || disc.includes('filosofía') || disc.includes('psicología') || disc.includes('rrhh') || disc.includes('recursos');
      }
      return true;
    };

    const matchesQuery = (book) => {
      if (!q) return true;
      return (
        (book.title || '').toLowerCase().includes(q) ||
        (book.discipline || '').toLowerCase().includes(q) ||
        (book.description || '').toLowerCase().includes(q) ||
        (book.filename || '').toLowerCase().includes(q) ||
        (book.id || '').toLowerCase().includes(q)
      );
    };

    const matchingBooks = all.filter(b => matchesCategory(b) && matchesQuery(b));
    const matchingIds = new Set(matchingBooks.map(b => b.id));

    // 1. Renderizar catálogo en lista filtrado
    this.renderCatalogList(matchingBooks);

    // Actualizar contador en lista
    const countList = document.getElementById('searchCountList');
    if (countList) {
      countList.textContent = `${matchingBooks.length} de ${all.length} documentos`;
    }

    // 2. Actualizar Estantería 3D (Lomos de libros)
    const spines = document.querySelectorAll('.bookshelf-rack .book-spine:not(.book-spine-upload)');
    spines.forEach(spine => {
      const bookId = spine.getAttribute('data-book-id');
      if (!q && !cat) {
        spine.classList.remove('book-dimmed', 'book-highlighted');
      } else if (matchingIds.has(bookId)) {
        spine.classList.remove('book-dimmed');
        spine.classList.add('book-highlighted');
      } else {
        spine.classList.remove('book-highlighted');
        spine.classList.add('book-dimmed');
      }
    });

    // Actualizar contador en 3D
    const count3D = this.elements.searchCount3D || document.getElementById('searchCount3D');
    if (count3D) {
      if (q || cat) {
        count3D.style.display = 'inline-block';
        count3D.textContent = `${matchingBooks.length} coincidente(s) de ${all.length}`;
      } else {
        count3D.style.display = 'none';
      }
    }
  },

  /**
   * Renderiza las tarjetas del Catálogo en formato lista (Modo Ejecutivo por Defecto)
   */
  renderCatalogList(booksToRender) {
    const docListEl = this.elements.docListEl || document.getElementById('cosmicDocList');
    if (!docListEl) return;

    if (!booksToRender || booksToRender.length === 0) {
      if (this.currentSearchQuery || this.activeCategory) {
        docListEl.innerHTML = '';
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'catalog-empty-state';

        const h4 = document.createElement('h4');
        h4.textContent = 'Sin resultados';

        const p = document.createElement('p');
        p.textContent = `No se encontraron módulos de capacitación que coincidan con "${this.currentSearchQuery || this.activeCategory}".`;

        emptyDiv.appendChild(h4);
        emptyDiv.appendChild(p);
        docListEl.appendChild(emptyDiv);
      } else {
        docListEl.innerHTML = `
          <div class="catalog-empty-state">
            <h4>Tu Catálogo de Capacitaciones está Listo</h4>
            <p>Aún no hay módulos de capacitación registrados en el servidor.</p>
            <button type="button" class="btn-primary-action btn-catalog-empty-upload" id="btnCatalogEmptyUpload">
              <span>+ Cargar Primer Documento</span>
            </button>
          </div>
        `;
        docListEl.querySelector('#btnCatalogEmptyUpload')?.addEventListener('click', () => {
          router.navigate('upload');
        });
      }
      return;
    }

    docListEl.innerHTML = '';

    booksToRender.forEach(book => {
      const ext = (book.filename || '').split('.').pop().toUpperCase() || 'PDF';
      const pages = book.sections?.length ? `${book.sections.length} secciones` : '1 sección';
      const size = book.filesize || '1.5 MB';
      const tag = book.discipline || 'General';
      const time = book.metadatos?.tiempo_estudio || '8 min';
      const isCustom = book.id?.startsWith('custom_') || !this.booksFromBackend.some(b => b.id === book.id);

      const card = document.createElement('div');
      card.className = 'cosmic-doc-card';
      card.dataset.bookId = book.id || '';

      // Información y metadatos del documento (Renderizado seguro con textContent)
      const infoContainer = document.createElement('div');
      infoContainer.style.cssText = 'display: flex; align-items: center; gap: 1rem; flex: 1; min-width: 0;';

      const formatTag = document.createElement('div');
      formatTag.className = 'cosmic-format-tag';
      formatTag.textContent = ext;

      const titleMetaCol = document.createElement('div');
      titleMetaCol.style.cssText = 'min-width: 0; flex: 1;';

      const h3 = document.createElement('h3');
      h3.style.cssText = 'font-size: 1.05rem; font-weight: 700; color: #ffffff; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
      h3.textContent = book.title || 'Documento sin título';

      const metaRow = document.createElement('div');
      metaRow.style.cssText = 'display: flex; align-items: center; gap: 0.6rem; font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.3rem; flex-wrap: wrap;';

      const idSpan = document.createElement('span');
      idSpan.style.cssText = 'font-family: monospace; opacity: 0.85;';
      idSpan.textContent = book.id || 'doc';

      const dot1 = document.createElement('span');
      dot1.textContent = '•';

      const pagesSpan = document.createElement('span');
      pagesSpan.textContent = pages;

      const dot2 = document.createElement('span');
      dot2.textContent = '•';

      const timeSpan = document.createElement('span');
      timeSpan.textContent = time;

      const dot3 = document.createElement('span');
      dot3.textContent = '•';

      const sizeSpan = document.createElement('span');
      sizeSpan.textContent = size;

      const tagSpan = document.createElement('span');
      tagSpan.className = 'catalog-doc-tag';
      tagSpan.textContent = tag;

      metaRow.appendChild(idSpan);
      metaRow.appendChild(dot1);
      metaRow.appendChild(pagesSpan);
      metaRow.appendChild(dot2);
      metaRow.appendChild(timeSpan);
      metaRow.appendChild(dot3);
      metaRow.appendChild(sizeSpan);
      metaRow.appendChild(tagSpan);

      titleMetaCol.appendChild(h3);
      titleMetaCol.appendChild(metaRow);

      infoContainer.appendChild(formatTag);
      infoContainer.appendChild(titleMetaCol);

      // Acciones del documento
      const actionsContainer = document.createElement('div');
      actionsContainer.className = 'catalog-card-actions';
      actionsContainer.style.cssText = 'display: flex; align-items: center; gap: 0.65rem; flex-shrink: 0;';

      const quizPill = document.createElement('span');
      quizPill.className = 'catalog-format-pill quiz-pill';
      quizPill.textContent = 'Quiz';

      const flashcardsPill = document.createElement('span');
      flashcardsPill.className = 'catalog-format-pill flashcards-pill';
      flashcardsPill.textContent = 'Flashcards';

      const btnStudy = document.createElement('button');
      btnStudy.type = 'button';
      btnStudy.className = 'btn-study-doc';
      btnStudy.dataset.bookId = book.id || '';
      btnStudy.textContent = 'Capacitar →';

      btnStudy.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectBookAndStudy(book, 'flashcards');
      });

      actionsContainer.appendChild(quizPill);
      actionsContainer.appendChild(flashcardsPill);
      actionsContainer.appendChild(btnStudy);

      if (isCustom) {
        const btnDelete = document.createElement('button');
        btnDelete.type = 'button';
        btnDelete.className = 'btn-delete-doc-item';
        btnDelete.dataset.bookId = book.id || '';
        btnDelete.title = 'Eliminar documento';
        btnDelete.textContent = '×';

        btnDelete.addEventListener('click', (e) => {
          e.stopPropagation();
          this.deleteCustomBook(book.id);
        });

        actionsContainer.appendChild(btnDelete);
      }

      card.appendChild(infoContainer);
      card.appendChild(actionsContainer);

      card.addEventListener('click', () => {
        this.openBookModal(book);
      });

      docListEl.appendChild(card);
    });
  },

  deleteCustomBook(bookId) {
    const customBooks = state.get().customBooks || [];
    const updated = customBooks.filter(b => b.id !== bookId);
    state.set({ customBooks: updated });
    try {
      localStorage.setItem('nuevamente_custom_books', JSON.stringify(updated));
    } catch {}
    this.renderShelf();
  },

  updateBackendMetric(isConnected) {
    const textEl = document.getElementById('metricBackendText');
    const dotEl = document.getElementById('metricBackendDot');
    if (!textEl) return;
    if (isConnected) {
      textEl.textContent = 'Conectado (FastAPI)';
      textEl.style.color = '#34d399';
      if (dotEl) {
        dotEl.style.background = '#10b981';
        dotEl.classList.remove('is-disconnected');
      }
    } else {
      textEl.textContent = 'Desconectado';
      textEl.style.color = '#f87171';
      if (dotEl) {
        dotEl.style.background = '#ef4444';
        dotEl.classList.add('is-disconnected');
      }
    }
  },

  getShortDisciplineTag(discipline) {
    if (!discipline) return 'MÓDULO';
    const map = {
      'Ingeniería de Software': 'SOFTWARE',
      'Arquitectura de Software': 'SOFTWARE',
      'Desarrollo Web & UX': 'DEV WEB',
      'Ciencia de Datos': 'DATA SCI',
      'Inteligencia Artificial': 'IA & DATA',
      'Cloud & DevOps': 'DEVOPS',
      'Neurociencias & Medicina': 'NEURO',
      'Ciencias Médicas & Biología': 'MEDICINA',
      'Derecho & Ciberseguridad': 'LEYES',
      'Ciencias Jurídicas & Derecho': 'DERECHO',
      'Economía & Negocios': 'ECONOMÍA',
      'Economía & Finanzas': 'FINANZAS',
      'Biología & Genética': 'GENÉTICA',
      'Ciberseguridad': 'SEGURIDAD',
      'Humanidades & Filosofía': 'HISTORIA',
      'Humanidades & Ciencias Sociales': 'HUMANID',
      'Psicología & Neurociencia': 'PSICOLOGÍA',
      'Física & Ciencias Exactas': 'FÍSICA',
      'Ciencias Generales': 'CIENCIA',
      'Ciencias & Disciplinas Generales': 'CIENCIA'
    };
    if (map[discipline]) return map[discipline];
    const firstWord = discipline.split(' ')[0].toUpperCase();
    return firstWord.length > 8 ? firstWord.slice(0, 8) : firstWord;
  },

  getLevelLabel(perfil) {
    const map = {
      principiante: 'Inicial / Inducción',
      intermedio: 'Operativo / Especialista',
      avanzado: 'Avanzado / Liderazgo'
    };
    return map[(perfil || '').toLowerCase()] || 'Corporativo';
  },

  createBookSpine(book) {
    const spine = document.createElement('div');
    const colorClass = `spine-${book.spineColor || 'navy'}`;
    spine.className = `book-spine ${colorClass}`;
    spine.setAttribute('data-book-id', book.id);
    spine.title = `${book.title} (${book.discipline})`;

    const shortTag = this.getShortDisciplineTag(book.discipline);

    const topRib = document.createElement('div');
    topRib.className = 'spine-top-rib';

    const titleSpan = document.createElement('span');
    titleSpan.className = 'spine-title-vertical';
    titleSpan.textContent = book.title || 'Documento';

    const codeSpan = document.createElement('span');
    codeSpan.className = 'spine-code-tag';
    codeSpan.textContent = shortTag;

    const bottomRib = document.createElement('div');
    bottomRib.className = 'spine-bottom-rib';

    spine.appendChild(topRib);
    spine.appendChild(titleSpan);
    spine.appendChild(codeSpan);
    spine.appendChild(bottomRib);

    spine.addEventListener('click', () => {
      this.openBookModal(book);
    });

    return spine;
  },

  createUploadSlotSpine() {
    const spine = document.createElement('div');
    spine.className = 'book-spine book-spine-upload';
    spine.title = 'Subir y procesar un nuevo documento';

    spine.innerHTML = `
      <div class="spine-top-rib"></div>
      <span class="spine-title-vertical">SUBIR NUEVO PDF</span>
      <span class="spine-code-tag">NUEVO</span>
      <div class="spine-bottom-rib"></div>
    `;

    spine.addEventListener('click', () => {
      router.navigate('upload');
    });

    return spine;
  },

  /**
   * Abre el modal del "Cuaderno Abierto" que sale a pantalla con las opciones de estudio
   */
  openBookModal(book) {
    this.currentSelectedBook = book;
    const {
      openBookOverlay, openedBadge, openedTitle, openedSummary,
      openedTime, openedSections, openedLevel, openedChips
    } = this.elements;

    if (!openBookOverlay) return;

    // Poblar Hoja Izquierda
    if (openedBadge) openedBadge.textContent = book.discipline;
    if (openedTitle) openedTitle.textContent = book.title;
    if (openedSummary) openedSummary.textContent = book.description;

    const meta = book.metadatos || {};
    if (openedTime) openedTime.textContent = meta.tiempo_estudio || '10 min';
    if (openedSections) openedSections.textContent = book.sections?.length || 1;
    if (openedLevel) openedLevel.textContent = this.getLevelLabel(meta.perfil);

    // Chips de conceptos clave de la primera sección (Renderizado seguro con textContent)
    if (openedChips) {
      const concepts = book.sections?.[0]?.key_concepts || ['Competencia Base', 'Procedimiento Clave', 'Buenas Prácticas'];
      openedChips.innerHTML = '';
      concepts.forEach(c => {
        const chip = document.createElement('span');
        chip.className = 'concept-chip';
        chip.textContent = typeof c === 'string' ? c : String(c ?? '');
        openedChips.appendChild(chip);
      });
    }

    // Mostrar modal
    openBookOverlay.style.display = 'flex';

    // Diagrama C: Consulta GET /documents/{id} para validar y enriquecer metadata
    if (book.id && !book.id.startsWith('mock_')) {
      apiClient.getDocumentById(book.id).then(docDetail => {
        if (docDetail) {
          if (docDetail.filename && !book.title) {
            if (openedTitle) openedTitle.textContent = docDetail.filename;
          }

          // Enriquecimiento con metadatos pedagógicos del documento (Sprint 3)
          if (typeof docDetail.estimated_time_minutes === 'number') {
            const timeStr = `${docDetail.estimated_time_minutes} min`;
            if (openedTime) openedTime.textContent = timeStr;
            if (book.metadatos) book.metadatos.tiempo_estudio = timeStr;
          }

          if (Array.isArray(docDetail.key_concepts) && docDetail.key_concepts.length > 0) {
            book.key_concepts = docDetail.key_concepts;
            if (book.sections && book.sections[0]) {
              book.sections[0].key_concepts = docDetail.key_concepts;
            }
            if (openedChips) {
              openedChips.innerHTML = '';
              docDetail.key_concepts.forEach(c => {
                const chip = document.createElement('span');
                chip.className = 'concept-chip';
                chip.textContent = typeof c === 'string' ? c : String(c ?? '');
                openedChips.appendChild(chip);
              });
            }
          }

          if (Array.isArray(docDetail.prerequisites) && docDetail.prerequisites.length > 0) {
            book.prerequisites = docDetail.prerequisites;
          }

          if (docDetail.summary && openedSummary) {
            openedSummary.textContent = docDetail.summary;
            book.description = docDetail.summary;
          }
        }
      }).catch(err => {
        console.warn(`[Bookshelf] Error en GET /documents/${book.id}:`, err.message);
        if (err.status === 404 || err.status >= 500) {
          statusDialog.showError({
            status: err.status || 500,
            code: err.code || 'DOCUMENT_NOT_FOUND',
            message: err.message || `No se pudo obtener el detalle del documento "${book.title}".`,
            details: [`Documento ID: ${book.id}`, err.message],
            filename: book.filename || book.title
          });
        }
      });
    }
  },

  closeBookModal() {
    if (this.elements.openBookOverlay) {
      this.elements.openBookOverlay.style.display = 'none';
    }
  },

  setupModalEvents() {
    const { openBookOverlay, btnCloseOverlay, btnStartStudying, studyChoiceCards } = this.elements;

    if (btnCloseOverlay) {
      btnCloseOverlay.addEventListener('click', () => this.closeBookModal());
    }

    if (openBookOverlay) {
      openBookOverlay.addEventListener('click', (e) => {
        if (e.target === openBookOverlay) this.closeBookModal();
      });
    }

    // Botón "Comenzar a Estudiar"
    if (btnStartStudying) {
      btnStartStudying.addEventListener('click', () => {
        if (!this.currentSelectedBook) return;
        this.selectBookAndStudy(this.currentSelectedBook, 'flashcards');
      });
    }

    // Tarjetas de estudio directo (Flashcards, Quiz, Video, Resumen)
    studyChoiceCards.forEach(card => {
      card.addEventListener('click', () => {
        if (!this.currentSelectedBook) return;
        const targetFormat = card.getAttribute('data-study-format') || 'flashcards';
        this.selectBookAndStudy(this.currentSelectedBook, targetFormat);
      });
    });

    if (this.elements.btnHeroUploadQuick) {
      this.elements.btnHeroUploadQuick.addEventListener('click', () => {
        router.navigate('upload');
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.code === 'Escape' && openBookOverlay && openBookOverlay.style.display === 'flex') {
        this.closeBookModal();
      }
    });
  },

  async selectBookAndStudy(book, targetFormat) {
    this.closeBookModal();

    // Estado inmediato para navegación rápida
    state.set({
      currentDocument: book,
      studyHub: {
        activeSectionId: book.sections?.[0]?.id || null,
        formats: null,
        formatsStatus: 'loading',
        activeFormat: targetFormat,
        currentCardIndex: 0,
        isFlipped: false
      }
    });

    router.navigate('study');

    // Tarea 7: Solicitar los formatos al Backend del libro abierto (GET /documents/{id}/formats)
    if (book.id) {
      try {
        const formats = await apiClient.getDocumentFormats(book.id);
        const resolvedFormats = formats?.formats || formats;
        const globalStatus = formats?.status || (resolvedFormats ? 'ready' : 'empty');
        state.set({
          studyHub: {
            ...state.get().studyHub,
            formats: resolvedFormats,
            formatsStatus: globalStatus
          }
        });
      } catch (err) {
        console.error('[StudyHub] Formatos no disponibles en backend para este documento:', err);
        state.set({
          studyHub: {
            ...state.get().studyHub,
            formatsStatus: 'error'
          }
        });

        const friendly = toFriendlyError(err);

        // Desplegar ventana de error para retroalimentación UX inmediata (Tarea 5 y 7)
        statusDialog.showError({
          status: friendly.status,
          code: friendly.code,
          message: friendly.message,
          details: [
            `Módulo: ${book.title}`,
            `Formato solicitado: ${targetFormat}`,
            ...friendly.details
          ],
          filename: book.filename || book.title
        });

        notifyWarning(
          friendly.title,
          friendly.message
        );
      }
    }
  }
};
