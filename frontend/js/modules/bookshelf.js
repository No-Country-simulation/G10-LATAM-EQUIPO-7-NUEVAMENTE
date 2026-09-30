/**
 * bookshelf.js
 * Controlador del Gran Librero Interactivo de NuevaMente y del Cuaderno Abierto.
 */

import { state } from '../state.js';
import { apiClient } from '../api/apiClient.js';
import { router } from './router.js';

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
        const customColors = ['gold-custom', 'ruby', 'cyan', 'purple', 'emerald', 'sapphire', 'amber'];
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
            spineColor: customColors[idx % customColors.length],
            description: doc.summary || doc.description || `Documento persistido en Backend y OCI Object Storage.`,
            filesize: doc.size_bytes ? `${(doc.size_bytes / (1024 * 1024)).toFixed(1)} MB` : '1.5 MB',
            status: doc.status || 'stored',
            metadatos: {
              document_id: docId,
              tiempo_estudio: doc.estimated_time || '8 min',
              perfil: doc.target_profile || 'intermediate',
              formato: ext
            },
            sections: doc.sections || [
              {
                id: `sec_${docId}`,
                title: formattedTitle,
                summary: doc.summary || `Contenido de ${formattedTitle} analizado por NuevaMente.`,
                key_concepts: [discipline, 'Concepto Clave', 'Persistencia OCI']
              }
            ]
          };
        });
        console.log(`[Bookshelf] ${this.booksFromBackend.length} libros recuperados desde Backend API.`);
      } else {
        this.booksFromBackend = [];
      }
    } catch (err) {
      console.log('[Bookshelf] Backend GET /documents no disponible aún o sin conexión:', err.message);
      this.booksFromBackend = [];
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
      subtitle.innerHTML = '<span class="status-dot-pulse" style="display:inline-block; margin-right:6px;"></span> Sincronizando libros con Backend API...';
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
      studyChoiceCards: document.querySelectorAll('.btn-study-choice-card')
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
    const customColors = ['gold-custom', 'ruby', 'cyan', 'purple', 'emerald', 'sapphire', 'amber'];

    // Priorizar customBooks subidos por el usuario en esta u otras sesiones
    customBooks.forEach((cDoc, idx) => {
      booksMap.set(cDoc.id, {
        ...cDoc,
        spineColor: cDoc.spineColor || customColors[idx % customColors.length]
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
        spineColor: currentDoc.spineColor || 'gold-custom'
      });
    }

    const books = Array.from(booksMap.values());
    this.allBooks = books;

    // Actualizar contadores métricos del Catálogo Cósmico
    const metricCount = document.getElementById('metricDocCount');
    if (metricCount) metricCount.textContent = books.length;

    const countList = document.getElementById('searchCountList');
    if (countList) countList.textContent = `${books.length} documento${books.length === 1 ? '' : 's'}`;

    // Renderizar catálogo en lista
    this.renderCatalogList(books);

    // Si no hay libros aún: mostrar estado vacío elegante en la estantería y catálogo
    if (books.length === 0) {
      const docListEl = document.getElementById('cosmicDocList');
      if (docListEl) {
        docListEl.innerHTML = `
          <div style="text-align: center; padding: 3rem 1rem; color: #a1a1aa;">
            <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">📚</div>
            <h4 style="font-size: 1.15rem; color: #f8fafc; margin-bottom: 0.35rem;">Tu Catálogo está Listo</h4>
            <p style="font-size: 0.9rem; margin-bottom: 1.25rem;">Aún no hay documentos en el servidor. Sube tu primer archivo PDF, Markdown o TXT.</p>
            <button type="button" class="btn-cosmic-primary" id="btnCatalogEmptyUpload" style="padding: 0.6rem 1.4rem;">
              <span>+ Subir Mi Primer Documento</span>
            </button>
          </div>
        `;
        docListEl.querySelector('#btnCatalogEmptyUpload')?.addEventListener('click', () => {
          router.navigate('upload');
        });
      }

      const emptyContainer = document.createElement('div');
      emptyContainer.className = 'shelf-empty-state';
      emptyContainer.innerHTML = `
        <div class="empty-shelf-card">
          <div class="empty-shelf-icon">📚</div>
          <h4>Tu Biblioteca está Lista</h4>
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

  getShortDisciplineTag(discipline) {
    if (!discipline) return 'LIBRO';
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
      principiante: 'Principiante',
      intermedio: 'Intermedio',
      avanzado: 'Avanzado'
    };
    return map[(perfil || '').toLowerCase()] || 'General';
  },

  createBookSpine(book) {
    const spine = document.createElement('div');
    const colorClass = `spine-${book.spineColor || 'navy'}`;
    spine.className = `book-spine ${colorClass}`;
    spine.setAttribute('data-book-id', book.id);
    spine.title = `${book.title} (${book.discipline})`;

    const shortTag = this.getShortDisciplineTag(book.discipline);

    spine.innerHTML = `
      <div class="spine-top-rib"></div>
      <span class="spine-title-vertical">${book.title}</span>
      <span class="spine-code-tag">${shortTag}</span>
      <div class="spine-bottom-rib"></div>
    `;

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

    // Chips de conceptos clave de la primera sección
    if (openedChips) {
      const concepts = book.sections?.[0]?.key_concepts || ['Concepto Base', 'Metodología', 'Estudio'];
      openedChips.innerHTML = concepts.map(c => `<span class="concept-chip">${c}</span>`).join('');
    }

    // Mostrar modal
    openBookOverlay.style.display = 'flex';
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
        if (formats && (formats.flashcards || formats.quiz || formats.summary || formats.tutorial || formats.formats)) {
          const resolvedFormats = formats.formats || formats;
          state.set({
            studyHub: {
              ...state.get().studyHub,
              formats: resolvedFormats
            }
          });
        }
      } catch (err) {
        console.log('[StudyHub] Formatos aún no disponibles en backend para este documento:', err.message);
      }
    }
  },

  /**
   * Renderiza las tarjetas del Catálogo en formato lista (Modo Ejecutivo)
   */
  renderCatalogList(booksToRender) {
    const docListEl = document.getElementById('cosmicDocList');
    if (!docListEl) return;

    if (!booksToRender || booksToRender.length === 0) {
      docListEl.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem; color: #a1a1aa;">
          <span style="font-size: 2rem;">🔍</span>
          <p style="margin-top: 0.5rem; font-size: 0.95rem;">No se encontraron documentos que coincidan con la búsqueda.</p>
        </div>
      `;
      return;
    }

    docListEl.innerHTML = booksToRender.map(book => {
      const ext = (book.filename || '').split('.').pop().toUpperCase() || 'PDF';
      const pages = book.sections?.length ? `${book.sections.length * 6} págs` : '12 págs';
      const size = book.filesize || '1.5 MB';
      const tag = book.discipline || 'General';

      return `
        <div class="cosmic-doc-card" data-book-id="${book.id}">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div class="cosmic-format-tag">${ext}</div>
            <div>
              <h3 style="font-size: 1rem; font-weight: 600; color: #ffffff; margin: 0;">${book.title}</h3>
              <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: #a1a1aa; margin-top: 0.25rem;">
                <span>${book.id || 'doc'}</span> • <span>${pages}</span> • <span>${size}</span> • <span style="background: rgba(88,28,135,0.4); color: #d8b4fe; padding: 2px 6px; border-radius: 4px;">${tag}</span>
              </div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 0.75rem; color: #d8b4fe; background: rgba(88,28,135,0.3); padding: 4px 8px; border-radius: 6px; border: 1px solid rgba(168,85,247,0.3);">Quiz</span>
            <span style="font-size: 0.75rem; color: #f472b6; background: rgba(88,28,135,0.3); padding: 4px 8px; border-radius: 6px; border: 1px solid rgba(244,114,182,0.3);">Flashcards</span>
            <button type="button" class="btn-cosmic-primary btn-study-doc" data-book-id="${book.id}" style="padding: 0.5rem 1rem; font-size: 0.75rem;">Estudiar →</button>
          </div>
        </div>
      `;
    }).join('');

    docListEl.querySelectorAll('.cosmic-doc-card').forEach(card => {
      const bookId = card.getAttribute('data-book-id');
      const book = (this.allBooks || []).find(b => b.id === bookId);
      if (!book) return;

      card.addEventListener('click', () => {
        this.openBookModal(book);
      });

      const btnStudy = card.querySelector('.btn-study-doc');
      if (btnStudy) {
        btnStudy.addEventListener('click', (e) => {
          e.stopPropagation();
          this.selectBookAndStudy(book, 'flashcards');
        });
      }
    });
  },

  /**
   * Configura eventos de búsqueda sincronizada (en Catálogo y en Estantería 3D)
   */
  setupSearchEvents() {
    const searchList = document.getElementById('searchDocList');
    const search3D = document.getElementById('searchDoc3D');
    const clearList = document.getElementById('btnClearSearchList');
    const clear3D = document.getElementById('btnClearSearch3D');
    const chips = document.querySelectorAll('.cosmic-chip');

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

    // Filtros por Categoría (Chips)
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const text = chip.textContent.trim().toLowerCase();
        if (text.startsWith('todos')) {
          this.activeCategory = null;
        } else if (text.includes('tecnología') || text.includes('cloud')) {
          this.activeCategory = 'tecnología';
        } else if (text.includes('legal') || text.includes('compliance')) {
          this.activeCategory = 'legal';
        } else if (text.includes('operaciones')) {
          this.activeCategory = 'operaciones';
        } else if (text.includes('rrhh') || text.includes('human')) {
          this.activeCategory = 'rrhh';
        } else {
          this.activeCategory = null;
        }
        this.filterBooks();
      });
    });
  },

  /**
   * Filtra tanto el Catálogo en Lista como la Estantería 3D en tiempo real
   */
  filterBooks() {
    const q = (this.currentSearchQuery || '').toLowerCase();
    const cat = this.activeCategory;
    const all = this.allBooks || [];

    const matchesCategory = (book) => {
      if (!cat) return true;
      const disc = (book.discipline || '').toLowerCase();
      if (cat === 'tecnología') {
        return disc.includes('software') || disc.includes('cloud') || disc.includes('ingeniería') || disc.includes('inteligencia') || disc.includes('datos');
      }
      if (cat === 'legal') {
        return disc.includes('derecho') || disc.includes('leyes') || disc.includes('jurídicas') || disc.includes('compliance');
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
        (book.filename || '').toLowerCase().includes(q)
      );
    };

    const matchingBooks = all.filter(b => matchesCategory(b) && matchesQuery(b));
    const matchingIds = new Set(matchingBooks.map(b => b.id));

    // 1. Actualizar Catálogo en Lista
    this.renderCatalogList(matchingBooks);

    // Actualizar Contador en Lista
    const countList = document.getElementById('searchCountList');
    if (countList) {
      countList.textContent = `${matchingBooks.length} de ${all.length} documentos`;
    }

    // 2. Actualizar Estantería 3D
    const spines = document.querySelectorAll('.shelf-row .book-spine:not(.book-spine-upload)');
    spines.forEach(spine => {
      const bookId = spine.getAttribute('data-book-id');
      if (!q && !cat) {
        spine.classList.remove('book-spine-dimmed', 'book-spine-highlighted');
      } else if (matchingIds.has(bookId)) {
        spine.classList.remove('book-spine-dimmed');
        spine.classList.add('book-spine-highlighted');
      } else {
        spine.classList.remove('book-spine-highlighted');
        spine.classList.add('book-spine-dimmed');
      }
    });

    // Actualizar Contador en 3D
    const count3D = document.getElementById('searchCount3D');
    if (count3D) {
      if (q || cat) {
        count3D.style.display = 'inline-block';
        count3D.textContent = `${matchingBooks.length} tomo(s) coincidente(s) de ${all.length}`;
      } else {
        count3D.style.display = 'none';
      }
    }
  }
};
