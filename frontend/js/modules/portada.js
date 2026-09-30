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
    // Si existe la portada legacy (para retrocompatibilidad)
    if (welcomePortada) {
      if (btnEnterLibrary) {
        btnEnterLibrary.addEventListener('click', (e) => {
          e.stopPropagation();
          this.enterLibrary();
        });
      }
      welcomePortada.addEventListener('click', (e) => {
        this.enterLibrary();
      });
    }

    // Botones de la Pantalla de Inicio Cósmica
    const btnHomeEnter = document.getElementById('btnHomeEnterLibrary');
    if (btnHomeEnter) {
      btnHomeEnter.addEventListener('click', (e) => {
        e.preventDefault();
        router.navigate('library');
      });
    }

    const btnHomeUpload = document.getElementById('btnHomeUpload');
    if (btnHomeUpload) {
      btnHomeUpload.addEventListener('click', (e) => {
        e.preventDefault();
        router.navigate('upload');
      });
    }

    // Toggle de Modo Interactivo (3D vs Lista)
    const btnToggleInteractive = document.getElementById('btnToggleInteractive');
    if (btnToggleInteractive) {
      btnToggleInteractive.addEventListener('click', (e) => {
        e.preventDefault();
        const isInteractive = document.body.classList.toggle('interactive-mode-active');
        btnToggleInteractive.innerHTML = isInteractive ? '<span>📋 Modo Lista</span>' : '<span>✦ Modo Interactivo</span>';
        router.navigate('library');
      });
    }

    // Permitir volver a Inicio al hacer clic en el logo de la cabecera
    if (brandHeader) {
      brandHeader.addEventListener('click', (e) => {
        e.preventDefault();
        router.navigate('home');
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
