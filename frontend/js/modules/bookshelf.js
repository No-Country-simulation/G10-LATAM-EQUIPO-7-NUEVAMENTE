/**
 * bookshelf.js
 * Controlador del Gran Librero Interactivo de NuevaMente y del Cuaderno Abierto.
 */

import { state } from '../state.js';
import { sampleLibrary } from '../data/sampleLibrary.js';
import { router } from './router.js';

export const bookshelf = {
  elements: {},
  currentSelectedBook: null,

  init() {
    this.bindElements();
    this.renderShelf();
    this.setupModalEvents();

    // Re-renderizar si cambia el documento cargado o la biblioteca
    state.subscribe((s) => {
      // Si el documento activo no está en la biblioteca visual, lo agregamos dinámicamente
      if (s.currentDocument && !sampleLibrary[s.currentDocument.id]) {
        this.renderShelf();
      }
    });
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
    if (shelfRow2) shelfRow2.innerHTML = '<div class="shelf-plank"></div>';

    const books = Object.values(sampleLibrary);
    
    // Si hay libros personalizados en customBooks o en currentDocument, los agregamos primero al estante
    const customBooks = state.get().customBooks || [];
    const customColors = ['gold-custom', 'ruby', 'cyan', 'purple', 'emerald'];
    
    customBooks.forEach((cDoc, idx) => {
      if (!books.find(b => b.id === cDoc.id)) {
        books.unshift({
          ...cDoc,
          spineColor: cDoc.spineColor || customColors[idx % customColors.length]
        });
      }
    });

    const currentDoc = state.get().currentDocument;
    if (currentDoc && !books.find(b => b.id === currentDoc.id)) {
      books.unshift({
        ...currentDoc,
        spineColor: currentDoc.spineColor || 'gold-custom'
      });
    }

    // Dividimos los libros entre el estante superior (Row 1) y el inferior (Row 2)
    const mid = Math.ceil(books.length / 2);
    const row1Books = books.slice(0, mid);
    const row2Books = books.slice(mid);

    row1Books.forEach(book => {
      shelfRow1.appendChild(this.createBookSpine(book));
    });

    if (shelfRow2) {
      row2Books.forEach(book => {
        shelfRow2.appendChild(this.createBookSpine(book));
      });

      // Agregar el Tomo Especial: "+ Subir Nuevo Documento" al final del estante
      shelfRow2.appendChild(this.createUploadSlotSpine());
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

  selectBookAndStudy(book, targetFormat) {
    state.set({
      currentDocument: book,
      studyHub: {
        activeSectionId: book.sections?.[0]?.id || null,
        activeFormat: targetFormat,
        currentCardIndex: 0,
        isFlipped: false
      }
    });

    this.closeBookModal();
    router.navigate('study');
  }
};
