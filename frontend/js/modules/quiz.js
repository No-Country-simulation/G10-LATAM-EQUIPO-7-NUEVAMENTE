/**
 * quiz.js
 * Lógica del Quiz interactivo con feedback instantáneo y justificación pedagógica.
 */

export const quiz = {
  elements: {},

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
    const { questionText, optionsList, feedbackBox } = this.elements;
    if (!questionText || !optionsList) return;

    if (feedbackBox) feedbackBox.style.display = 'none';

    if (!quizData || !quizData.pregunta) {
      questionText.textContent = 'No hay preguntas de quiz configuradas para esta sección.';
      optionsList.innerHTML = '';
      return;
    }

    questionText.textContent = quizData.pregunta;
    optionsList.innerHTML = '';

    const letters = ['A', 'B', 'C', 'D'];
    (quizData.opciones || []).forEach((opcion, index) => {
      const btn = document.createElement('button');
      btn.className = 'quiz-option-btn';
      btn.innerHTML = `<strong>${letters[index] || index + 1})</strong> <span>${opcion}</span>`;

      btn.addEventListener('click', () => {
        this.handleAnswer(index, quizData);
      });

      optionsList.appendChild(btn);
    });
  },

  handleAnswer(selectedIndex, quizData) {
    const { feedbackBox, feedbackBadge, feedbackText, optionsList } = this.elements;
    if (!optionsList) return;

    const allButtons = optionsList.querySelectorAll('.quiz-option-btn');
    allButtons.forEach(b => b.disabled = true);

    const isCorrect = selectedIndex === quizData.correcta;

    if (isCorrect) {
      allButtons[selectedIndex]?.classList.add('correct');
      if (feedbackBadge) {
        feedbackBadge.className = 'feedback-badge correct';
        feedbackBadge.textContent = '✓ ¡Respuesta Correcta!';
      }
    } else {
      allButtons[selectedIndex]?.classList.add('incorrect');
      allButtons[quizData.correcta]?.classList.add('correct');
      if (feedbackBadge) {
        feedbackBadge.className = 'feedback-badge incorrect';
        feedbackBadge.textContent = '✕ Respuesta Incorrecta';
      }
    }

    if (feedbackText) {
      feedbackText.textContent = quizData.explicacion || 'El anclaje conceptual del documento fundamenta esta respuesta.';
    }

    if (feedbackBox) {
      feedbackBox.style.display = 'flex';
    }
  }
};
