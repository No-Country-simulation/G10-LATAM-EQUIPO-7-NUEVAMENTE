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

    const question = quizData.question || quizData.pregunta;
    const options = quizData.options || quizData.opciones;

    if (!quizData || !question) {
      questionText.textContent = 'No hay preguntas de quiz configuradas para esta sección.';
      optionsList.innerHTML = '';
      return;
    }

    questionText.textContent = question;
    optionsList.innerHTML = '';

    const letters = ['A', 'B', 'C', 'D'];
    (options || []).forEach((opcion, index) => {
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

    const correctIndex = quizData.correct_answer !== undefined ? quizData.correct_answer : quizData.correcta;
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
      feedbackText.textContent = quizData.explanation || quizData.explicacion || 'El anclaje conceptual del documento fundamenta esta respuesta.';
    }

    if (feedbackBox) {
      feedbackBox.style.display = 'flex';
    }
  }
};
