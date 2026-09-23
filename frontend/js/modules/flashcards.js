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
    this.cards = cardsList || [];
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
      if (frontText) frontText.textContent = 'No hay flashcards disponibles para esta sección.';
      if (backText) backText.textContent = '';
      if (progressTop) progressTop.textContent = '0 / 0';
      if (counterText) counterText.textContent = '0 de 0';
      if (btnPrev) btnPrev.disabled = true;
      if (btnNext) btnNext.disabled = true;
      return;
    }

    const currentCard = this.cards[this.currentIndex];
    const total = this.cards.length;
    const currentNum = this.currentIndex + 1;

    if (frontText) frontText.textContent = currentCard.front || currentCard.frente;
    if (backText) backText.textContent = currentCard.back || currentCard.dorso;
    if (hintText) hintText.textContent = currentCard.didactic_hint || currentCard.pista_didactica || 'Reflexiona sobre el concepto clave de la pregunta.';

    if (progressTop) progressTop.textContent = `${currentNum} / ${total}`;
    if (counterText) counterText.textContent = `Tarjeta ${currentNum} de ${total}`;

    if (btnPrev) btnPrev.disabled = this.currentIndex === 0;
    if (btnNext) btnNext.disabled = this.currentIndex === total - 1;
  }
};
