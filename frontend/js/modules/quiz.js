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
    // Normalizar entrada a un arreglo de preguntas
    if (Array.isArray(quizData)) {
      this.questions = quizData;
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
      questionText.textContent = 'El cuestionario de autoevaluación (Quiz) está en proceso de generación.';
      optionsList.innerHTML = `
        <div style="text-align: center; padding: 2rem 1rem; color: var(--text-secondary);">
          <p style="font-size: 0.95rem; margin-bottom: 0.5rem;">
            Las preguntas de autoevaluación se generarán automáticamente a partir del contenido indexado por el Backend.
          </p>
          <span style="font-size: 0.8rem; color: var(--accent-gold);">
            Consejo: Asegúrate de que el pipeline RAG haya finalizado de analizar tu documento.
          </span>
        </div>
      `;
      return;
    }

    const currentQ = this.questions[this.currentIndex];
    const question = currentQ.question || currentQ.pregunta || currentQ.prompt || currentQ.text;
    const options = currentQ.options || currentQ.opciones || currentQ.choices || [];
    const totalQ = this.questions.length;
    const qNum = this.currentIndex + 1;

    questionText.innerHTML = totalQ > 1
      ? `<span style="font-size: 0.82rem; font-weight: 700; color: var(--accent-cyan); display: block; margin-bottom: 0.35rem;">Pregunta ${qNum} de ${totalQ}</span>${question}`
      : question;

    optionsList.innerHTML = '';

    const letters = ['A', 'B', 'C', 'D', 'E'];
    options.forEach((opcion, index) => {
      const btn = document.createElement('button');
      btn.className = 'quiz-option-btn';
      btn.innerHTML = `<strong>${letters[index] || index + 1})</strong> <span>${opcion}</span>`;

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

    let correctIndex = currentQ.correct_answer;
    if (correctIndex === undefined) correctIndex = currentQ.correct_index;
    if (correctIndex === undefined) correctIndex = currentQ.correcta;
    if (correctIndex === undefined && typeof currentQ.answer === 'number') correctIndex = currentQ.answer;

    const isCorrect = selectedIndex === correctIndex;

    if (isCorrect) {
      allButtons[selectedIndex]?.classList.add('correct');
      if (feedbackBadge) {
        feedbackBadge.className = 'feedback-badge correct';
        feedbackBadge.textContent = '¡Respuesta Correcta!';
      }
    } else {
      allButtons[selectedIndex]?.classList.add('incorrect');
      if (correctIndex !== undefined && allButtons[correctIndex]) {
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
        || 'El anclaje conceptual del documento fundamenta esta respuesta.';
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
