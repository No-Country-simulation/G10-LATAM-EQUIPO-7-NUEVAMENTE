/**
 * flashcards.js
 * Lógica del formato Flashcards 3D: volteo, atajos de teclado y navegación.
 */

import { state } from '../state.js';

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
        if (frontText) frontText.textContent = 'Flashcards No Disponibles';
        if (backText) backText.textContent = this.formatMeta.errorMessage || 'Ocurrió un error al procesar este formato en el backend.';
        if (hintText) hintText.textContent = 'Puedes continuar estudiando con el Quiz interactivo.';
      } else if (this.formatMeta?.status === 'no_results') {
        if (frontText) frontText.textContent = 'Sin conceptos suficientes';
        if (backText) backText.textContent = 'El documento no contiene suficiente información para extraer flashcards.';
        if (hintText) hintText.textContent = 'Intenta con un documento más extenso o detallado.';
      } else {
        if (frontText) frontText.textContent = 'No hay flashcards generadas aún para este documento.';
        if (backText) backText.textContent = 'Las flashcards se generarán automáticamente a través del pipeline RAG.';
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
        || 'Explicación didáctica';
    }
    if (hintText) {
      hintText.textContent = currentCard.didactic_hint 
        || currentCard.pista_didactica 
        || currentCard.hint 
        || currentCard.pista 
        || 'Reflexiona sobre el concepto clave de la pregunta.';
    }

    if (progressTop) progressTop.textContent = `${currentNum} / ${total}`;
    if (counterText) counterText.textContent = `Tarjeta ${currentNum} de ${total}`;

    if (btnPrev) btnPrev.disabled = this.currentIndex === 0;
    if (btnNext) btnNext.disabled = this.currentIndex === total - 1;
  }
};
