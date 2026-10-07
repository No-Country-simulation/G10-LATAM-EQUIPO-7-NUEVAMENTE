/**
 * flashcards.js
 * Lógica del formato Flashcards 3D: volteo, atajos de teclado y navegación.
 */

import { state } from '../state.js';
import { toFriendlyError } from '../utils/friendlyError.js';

export const flashcards = {
  elements: {},
  cards: [],
  currentIndex: 0,
  isFlipped: false,

  init() {
    this.bindElements();
    this.setupListeners();
  },

  bindElements() {
    this.elements = {
      card: document.getElementById('currentCard'),
      frontText: document.getElementById('cardFrontText'),
      backText: document.getElementById('cardBackText'),
      hintText: document.getElementById('cardHintText'),
      progressTop: document.getElementById('cardProgressTop'),
      counterText: document.getElementById('cardCounter'),
      btnPrev: document.getElementById('btnPrevCard'),
      btnNext: document.getElementById('btnNextCard'),
      btnFlip: document.getElementById('btnFlipCard')
    };
  },

  setupListeners() {
    const { card, btnFlip, btnPrev, btnNext } = this.elements;

    if (card) {
      card.addEventListener('click', () => this.toggleFlip());
    }

    if (btnFlip) {
      btnFlip.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleFlip();
      });
    }

    if (btnPrev) {
      btnPrev.addEventListener('click', (e) => {
        e.stopPropagation();
        this.prevCard();
      });
    }

    if (btnNext) {
      btnNext.addEventListener('click', (e) => {
        e.stopPropagation();
        this.nextCard();
      });
    }

    // Atajos de teclado en el Centro de Estudio
    document.addEventListener('keydown', (e) => {
      const s = state.get();
      if (s.activeTab !== 'study' || s.studyHub.activeFormat !== 'flashcards') return;

      if (e.code === 'Space' || e.code === 'Enter') {
        e.preventDefault();
        this.toggleFlip();
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        this.nextCard();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        this.prevCard();
      }
    });
  },

  render(cardsList) {
    this.formatMeta = {
      status: cardsList?.status || 'success',
      errorMessage: cardsList?.error_message || null,
      title: cardsList?.content?.title || cardsList?.title || null,
      instructions: cardsList?.content?.instructions || cardsList?.instructions || null
    };

    if (Array.isArray(cardsList)) {
      this.cards = cardsList;
    } else if (cardsList && cardsList.content && Array.isArray(cardsList.content.cards)) {
      this.cards = cardsList.content.cards;
    } else if (cardsList && Array.isArray(cardsList.cards)) {
      this.cards = cardsList.cards;
    } else if (cardsList && Array.isArray(cardsList.flashcards)) {
      this.cards = cardsList.flashcards;
    } else if (cardsList && Array.isArray(cardsList.items)) {
      this.cards = cardsList.items;
    } else {
      this.cards = [];
    }
    this.currentIndex = 0;
    this.isFlipped = false;
    this.updateCardDisplay();
  },

  toggleFlip() {
    if (this.cards.length === 0) return;
    this.isFlipped = !this.isFlipped;
    if (this.elements.card) {
      if (this.isFlipped) {
        this.elements.card.classList.add('flipped');
      } else {
        this.elements.card.classList.remove('flipped');
      }
    }
  },

  nextCard() {
    if (this.currentIndex < this.cards.length - 1) {
      this.currentIndex++;
      this.isFlipped = false;
      this.updateCardDisplay();
    }
  },

  prevCard() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.isFlipped = false;
      this.updateCardDisplay();
    }
  },

  updateCardDisplay() {
    const { card, frontText, backText, hintText, progressTop, counterText, btnPrev, btnNext } = this.elements;
    if (!card) return;

    card.classList.remove('flipped');

    if (this.cards.length === 0) {
      if (this.formatMeta?.status === 'failed') {
        const friendly = toFriendlyError({ message: this.formatMeta.errorMessage });
        if (frontText) frontText.textContent = 'Tarjetas de Refuerzo en Proceso';
        if (backText) backText.textContent = friendly.message;
        if (hintText) hintText.textContent = 'Consejo: Puedes pulsar "Sincronizar Formatos" arriba para consultar si ya están disponibles.';
      } else if (this.formatMeta?.status === 'no_results') {
        if (frontText) frontText.textContent = 'Sin competencias suficientes';
        if (backText) backText.textContent = 'El documento corporativo no contiene suficiente información para extraer tarjetas de refuerzo.';
        if (hintText) hintText.textContent = 'Intenta con un manual o directriz con mayor detalle operativo.';
      } else if (this.formatMeta?.status === 'processing') {
        if (frontText) frontText.textContent = 'Generando Tarjetas de Refuerzo...';
        if (backText) backText.textContent = 'El pipeline de IA está procesando las directrices y competencias del material.';
        if (hintText) hintText.textContent = 'Por favor espera unos instantes mientras se sintetiza el contenido de capacitación.';
      } else {
        if (frontText) frontText.textContent = 'No hay tarjetas de refuerzo generadas aún para este documento.';
        if (backText) backText.textContent = 'Las tarjetas de refuerzo se generarán automáticamente a través del pipeline RAG.';
        if (hintText) hintText.textContent = 'Consejo: Sube un documento o espera a que el Backend complete la indexación.';
      }
      if (progressTop) progressTop.textContent = '0 / 0';
      if (counterText) counterText.textContent = '0 de 0';
      if (btnPrev) btnPrev.disabled = true;
      if (btnNext) btnNext.disabled = true;
      return;
    }

    const currentCard = this.cards[this.currentIndex];
    const total = this.cards.length;
    const currentNum = this.currentIndex + 1;

    if (frontText) {
      frontText.textContent = currentCard.front 
        || currentCard.frente 
        || currentCard.question 
        || currentCard.pregunta 
        || currentCard.concept 
        || 'Concepto clave';
    }
    if (backText) {
      backText.textContent = currentCard.back 
        || currentCard.dorso 
        || currentCard.answer 
        || currentCard.respuesta 
        || currentCard.definition 
        || 'Fundamento y justificación técnica';
    }
    if (hintText) {
      hintText.textContent = currentCard.didactic_hint 
        || currentCard.pista_didactica 
        || currentCard.hint 
        || currentCard.pista 
        || 'Analiza el procedimiento y las directrices operativas de la organización.';
    }

    if (progressTop) progressTop.textContent = `${currentNum} / ${total}`;
    if (counterText) counterText.textContent = `Tarjeta ${currentNum} de ${total}`;

    if (btnPrev) btnPrev.disabled = this.currentIndex === 0;
    if (btnNext) btnNext.disabled = this.currentIndex === total - 1;
  }
};
