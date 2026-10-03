/**
 * bookshelf.js
 * Controlador del Gran Librero Interactivo de NuevaMente y del Cuaderno Abierto.
 */

import { state } from '../state.js';
import { apiClient } from '../api/apiClient.js';
import { router } from './router.js';
import { statusDialog } from './statusDialog.js';
import { notifyError, notifyWarning } from './notifications.js';

export const bookshelf = {
  elements: {},
  currentSelectedBook: null,
  booksFromBackend: [],
  isLoadingBackend: false,

  async init() {
    this.bindElements();
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
      console.warn('[Bookshelf] Backend GET /documents no disponible aún o sin conexión:', err.message);
      this.booksFromBackend = [];
      if (err.status >= 500 || err.status === 502) {
        statusDialog.showError({
          status: err.status,
          code: err.code || 'DOCUMENTS_FETCH_ERROR',
          message: err.message || 'Error al obtener la lista de documentos desde el backend.',
          details: err.details || ['GET /api/v1/documents', err.message]
        });
      }
      notifyWarning(
        `Biblioteca (${err.status || 0})`,
        err.status === 0
          ? 'Backend fuera de línea. Mostrando estantería local.'
          : (err.message || 'No fue posible sincronizar los libros.')
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
      studyChoiceCards: document.querySelectorAll('.btn-study-choice-card'),

      // Botón de Carga Rápida en el Hero de la Biblioteca
      btnHeroUploadQuick: document.getElementById('btnHeroUploadQuick')
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

    // Si no hay libros aún: mostrar estado vacío elegante en la estantería
    if (books.length === 0) {
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
      const concepts = book.sections?.[0]?.key_concepts || ['Competencia Base', 'Procedimiento Clave', 'Buenas Prácticas'];
      openedChips.innerHTML = concepts.map(c => `<span class="concept-chip">${c}</span>`).join('');
    }

    // Mostrar modal
    openBookOverlay.style.display = 'flex';

    // Diagrama C: Consulta GET /documents/{id} para validar y enriquecer metadata
    if (book.id && !book.id.startsWith('mock_')) {
      apiClient.getDocumentById(book.id).then(docDetail => {
        if (docDetail && openedTitle) {
          if (docDetail.filename && !book.title) {
            openedTitle.textContent = docDetail.filename;
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

        // Desplegar ventana de error para retroalimentación UX inmediata (Tarea 5 y 7)
        statusDialog.showError({
          status: err.status || 500,
          code: err.code || 'FORMATS_NOT_AVAILABLE',
          message: err.message || `No fue posible cargar los formatos de capacitación para "${book.title}".`,
          details: [
            `Documento ID: ${book.id}`,
            `Formato solicitado: ${targetFormat}`,
            err.message
          ],
          filename: book.filename || book.title
        });

        notifyError(
          `Formatos No Disponibles (${err.status || 500})`,
          err.message || 'Error al obtener formatos desde el servidor.'
        );
      }
    }
  }
};
