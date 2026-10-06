/**
 * quiz.js
 * Lógica del Quiz interactivo con feedback instantáneo y justificación pedagógica.
 * Soporta colecciones de preguntas del Backend real (Tarea 8).
 */

export const quiz = {
  elements: {},
  questions: [],
  currentIndex: 0,

  init() {
    this.elements = {
      questionText: document.getElementById('quizQuestionText'),
      optionsList: document.getElementById('quizOptionsList'),
      feedbackBox: document.getElementById('quizFeedbackBox'),
      feedbackBadge: document.getElementById('quizFeedbackBadge'),
      feedbackText: document.getElementById('quizFeedbackText')
    };
  },

  render(quizData) {
    this.quizMeta = {
      status: quizData?.status || 'success',
      errorMessage: quizData?.error_message || null,
      title: quizData?.content?.title || quizData?.title || null,
      instructions: quizData?.content?.instructions || quizData?.instructions || null
    };

    // Normalizar entrada a un arreglo de preguntas (soporta content.questions y direct questions)
    if (Array.isArray(quizData)) {
      this.questions = quizData;
    } else if (quizData && quizData.content && Array.isArray(quizData.content.questions)) {
      this.questions = quizData.content.questions;
    } else if (quizData && Array.isArray(quizData.questions)) {
      this.questions = quizData.questions;
    } else if (quizData && (quizData.question || quizData.pregunta)) {
      this.questions = [quizData];
    } else {
      this.questions = [];
    }

    this.currentIndex = 0;
    this.renderCurrentQuestion();
  },

  renderCurrentQuestion() {
    const { questionText, optionsList, feedbackBox } = this.elements;
    if (!questionText || !optionsList) return;

    if (feedbackBox) feedbackBox.style.display = 'none';

    if (this.questions.length === 0) {
      if (this.quizMeta?.status === 'failed') {
        questionText.textContent = 'Evaluación de Competencias (Quiz) No Disponible';
        optionsList.innerHTML = '';

        const errorDiv = document.createElement('div');
        errorDiv.style.textAlign = 'center';
        errorDiv.style.padding = '2rem 1rem';
        errorDiv.style.color = '#ef4444';

        const p = document.createElement('p');
        p.style.fontSize = '0.95rem';
        p.style.marginBottom = '0.5rem';
        p.textContent = this.quizMeta.errorMessage || 'Ocurrió un error al generar las preguntas de evaluación de competencias.';

        const span = document.createElement('span');
        span.style.fontSize = '0.8rem';
        span.style.color = 'var(--text-secondary)';
        span.textContent = 'Puedes continuar reforzando conocimientos con las Tarjetas de Refuerzo mientras el sistema reintenta este formato.';

        errorDiv.appendChild(p);
        errorDiv.appendChild(span);
        optionsList.appendChild(errorDiv);
      } else if (this.quizMeta?.status === 'no_results') {
        questionText.textContent = 'Sin preguntas de evaluación generadas';
        optionsList.innerHTML = `
          <div style="text-align: center; padding: 2rem 1rem; color: var(--text-secondary);">
            <p style="font-size: 0.95rem; margin-bottom: 0.5rem;">
              El documento corporativo no contiene suficiente información para formular una evaluación.
            </p>
          </div>
        `;
      } else if (this.quizMeta?.status === 'processing') {
        questionText.textContent = 'Generando Evaluación de Competencias...';
        optionsList.innerHTML = `
          <div style="text-align: center; padding: 2rem 1rem; color: var(--text-secondary);">
            <p style="font-size: 0.95rem; margin-bottom: 0.5rem;">
              El pipeline de IA está formulando las preguntas a partir del material corporativo indexado.
            </p>
            <span style="font-size: 0.8rem; color: var(--accent-gold);">
              Por favor espera unos instantes.
            </span>
          </div>
        `;
      } else {
        questionText.textContent = 'La evaluación de competencias (Quiz) está en proceso de generación.';
        optionsList.innerHTML = `
          <div style="text-align: center; padding: 2rem 1rem; color: var(--text-secondary);">
            <p style="font-size: 0.95rem; margin-bottom: 0.5rem;">
              Las preguntas de evaluación de competencias se generarán automáticamente a partir del contenido indexado por el Backend.
            </p>
            <span style="font-size: 0.8rem; color: var(--accent-gold);">
              Consejo: Asegúrate de que el pipeline RAG haya finalizado de analizar el documento corporativo.
            </span>
          </div>
        `;
      }
      return;
    }

    const currentQ = this.questions[this.currentIndex];
    const question = currentQ.question || currentQ.pregunta || currentQ.prompt || currentQ.text || '';
    const options = currentQ.options || currentQ.opciones || currentQ.choices || [];
    const totalQ = this.questions.length;
    const qNum = this.currentIndex + 1;

    // Renderizado seguro de la pregunta: sin innerHTML con datos del LLM/Backend para prevenir XSS
    questionText.textContent = '';
    if (totalQ > 1) {
      const badge = document.createElement('span');
      badge.style.fontSize = '0.82rem';
      badge.style.fontWeight = '700';
      badge.style.color = 'var(--accent-cyan)';
      badge.style.display = 'block';
      badge.style.marginBottom = '0.35rem';
      badge.textContent = `Pregunta ${qNum} de ${totalQ}`;
      questionText.appendChild(badge);
      questionText.appendChild(document.createTextNode(question));
    } else {
      questionText.textContent = question;
    }

    optionsList.innerHTML = '';

    const letters = ['A', 'B', 'C', 'D', 'E'];
    options.forEach((opcion, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'quiz-option-btn';

      const strong = document.createElement('strong');
      strong.textContent = `${letters[index] || index + 1}) `;

      const span = document.createElement('span');
      span.textContent = typeof opcion === 'string' ? opcion : String(opcion ?? '');

      btn.appendChild(strong);
      btn.appendChild(span);

      btn.addEventListener('click', () => {
        this.handleAnswer(index, currentQ);
      });

      optionsList.appendChild(btn);
    });
  },

  handleAnswer(selectedIndex, currentQ) {
    const { feedbackBox, feedbackBadge, feedbackText, optionsList } = this.elements;
    if (!optionsList) return;

    const allButtons = optionsList.querySelectorAll('.quiz-option-btn');
    allButtons.forEach(b => b.disabled = true);

    const options = currentQ.options || currentQ.opciones || currentQ.choices || [];

    // Resolver correctIndex soportando tanto texto exacto como número de índice
    let correctIndex = -1;
    const rawCorrect = currentQ.correct_answer ?? currentQ.correct_index ?? currentQ.correcta ?? currentQ.answer;

    if (typeof rawCorrect === 'number') {
      correctIndex = rawCorrect;
    } else if (typeof rawCorrect === 'string') {
      // Búsqueda insensible a mayúsculas y espacios en la lista de opciones
      correctIndex = options.findIndex(opt => opt.trim().toLowerCase() === rawCorrect.trim().toLowerCase());
      if (correctIndex === -1 && !isNaN(parseInt(rawCorrect, 10))) {
        correctIndex = parseInt(rawCorrect, 10);
      }
    }

    const isCorrect = selectedIndex === correctIndex;

    if (isCorrect) {
      allButtons[selectedIndex]?.classList.add('correct');
      if (feedbackBadge) {
        feedbackBadge.className = 'feedback-badge correct';
        feedbackBadge.textContent = '¡Respuesta Correcta!';
      }
    } else {
      allButtons[selectedIndex]?.classList.add('incorrect');
      if (correctIndex >= 0 && allButtons[correctIndex]) {
        allButtons[correctIndex].classList.add('correct');
      }
      if (feedbackBadge) {
        feedbackBadge.className = 'feedback-badge incorrect';
        feedbackBadge.textContent = 'Respuesta Incorrecta';
      }
    }

    if (feedbackText) {
      feedbackText.textContent = currentQ.explanation 
        || currentQ.explicacion 
        || currentQ.justification 
        || 'El anclaje conceptual del manual o directriz corporativa fundamenta esta respuesta.';
    }

    // Si hay más preguntas, ofrecer botón para avanzar
    if (feedbackBox) {
      feedbackBox.style.display = 'flex';

      const existingNextBtn = feedbackBox.querySelector('.btn-next-question');
      if (existingNextBtn) existingNextBtn.remove();

      if (this.currentIndex < this.questions.length - 1) {
        const nextBtn = document.createElement('button');
        nextBtn.type = 'button';
        nextBtn.className = 'btn-primary-action btn-next-question';
        nextBtn.style.marginTop = '0.75rem';
        nextBtn.style.alignSelf = 'flex-end';
        nextBtn.innerHTML = '<span>Siguiente Pregunta &rarr;</span>';
        nextBtn.addEventListener('click', () => {
          this.currentIndex++;
          this.renderCurrentQuestion();
        });
        feedbackBox.appendChild(nextBtn);
      }
    }
  }
};
