/**
 * portada.js
 * Gestiona la portada de bienvenida interactiva y la transición cinematográfica
 * de apertura hacia La Biblioteca de NuevaMente.
 */

import { router } from './router.js';

export const portada = {
  elements: {},
  isClosing: false,

  init() {
    this.bindElements();
    this.setupEvents();
  },

  bindElements() {
    this.elements = {
      welcomePortada: document.getElementById('welcomePortada'),
      portadaCard: document.getElementById('portadaCard'),
      btnEnterLibrary: document.getElementById('btnEnterLibrary'),
      brandHeader: document.getElementById('brandHeader')
    };
  },

  setupEvents() {
    const { welcomePortada, portadaCard, btnEnterLibrary, brandHeader } = this.elements;
    if (!welcomePortada) return;

    // Al hacer clic en el botón principal de ingreso
    if (btnEnterLibrary) {
      btnEnterLibrary.addEventListener('click', (e) => {
        e.stopPropagation();
        this.enterLibrary();
      });
    }

    // Al hacer clic en el fondo de la portada
    welcomePortada.addEventListener('click', (e) => {
      // Si hace clic en la tarjeta o en el fondo, ingresa al librero
      this.enterLibrary();
    });

    // Permitir volver a abrir la portada al hacer clic en el logo de la cabecera
    if (brandHeader) {
      brandHeader.addEventListener('click', (e) => {
        e.preventDefault();
        this.openPortada();
      });
    }
  },

  /**
   * Transición de apertura hacia La Biblioteca de NuevaMente
   */
  enterLibrary() {
    if (this.isClosing) return;
    this.isClosing = true;

    const { welcomePortada } = this.elements;
    if (!welcomePortada) return;

    // Efecto de apertura cinematográfica: fade-out y zoom sutil
    welcomePortada.classList.add('portada-opening');

    // Navegar y enfocar la vista del librero
    router.navigate('library');

    setTimeout(() => {
      welcomePortada.style.display = 'none';
      welcomePortada.classList.remove('portada-opening');
      this.isClosing = false;
    }, 850);
  },

  /**
   * Reabre la portada de bienvenida (útil para demostraciones)
   */
  openPortada() {
    const { welcomePortada } = this.elements;
    if (!welcomePortada) return;

    this.isClosing = false;
    welcomePortada.style.display = 'flex';
    welcomePortada.classList.remove('portada-opening');
    welcomePortada.classList.add('portada-enter');

    setTimeout(() => {
      welcomePortada.classList.remove('portada-enter');
    }, 500);
  }
};
