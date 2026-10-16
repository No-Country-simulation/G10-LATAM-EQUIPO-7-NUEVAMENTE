const dimensions = {
  relevance: ['Relevancia · ¿Responde al objetivo?', 'Compara términos significativos del contenido con la fuente y el contexto de aprendizaje.', 'Valora si el contenido responde al tema y al objetivo, aunque utilice otras palabras.'],
  coherence: ['Coherencia · ¿Se entiende y mantiene consistencia?', 'Revisa señales de estructura y organización propias del formato.', 'Analiza claridad, continuidad de ideas y posibles contradicciones.'],
  adaptation: ['Adaptación didáctica · ¿Es adecuado para quien aprende?', 'Contrasta señales del contenido con el perfil y el nivel de detalle solicitado.', 'Valora lenguaje, explicaciones y profundidad según el destinatario y el objetivo.'],
  support: ['Respaldo documental · ¿La evidencia sostiene lo afirmado?', 'Contrasta términos del contenido factual con los fragmentos utilizados como evidencia.', 'Comprueba si las afirmaciones están sustentadas y señala información no respaldada.']
};
document.querySelectorAll('[data-dimension]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-dimension]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  const [title, heuristic, semantic] = dimensions[button.dataset.dimension];
  document.querySelector('#dimension-title').textContent = title;
  document.querySelector('#heuristic-description').textContent = heuristic;
  document.querySelector('#semantic-description').textContent = semantic;
}));
const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
const toggle = document.querySelector('#motion');
let paused = false;
let visible = true;
let timer = null;
let step = 0;
function updateMotion() {
  window.clearInterval(timer);
  const stopped = paused || !visible || document.hidden || preference.matches;
  document.body.classList.toggle('paused', stopped);
  toggle.hidden = preference.matches;
  document.querySelectorAll('.stage').forEach(node => node.classList.remove('current'));
  if (stopped) return;
  const stages = [['validate'], ['heuristic', 'semantic'], ['decision'], ['result']];
  const advance = () => {
    const active = stages[step % stages.length];
    document.querySelectorAll('.stage').forEach(node => node.classList.toggle('current', active.some(name => node.classList.contains(name))));
    step += 1;
  };
  advance();
  timer = window.setInterval(advance, 2500);
}
toggle.addEventListener('click', () => {
  paused = !paused;
  toggle.textContent = paused ? 'Reanudar animación' : 'Pausar animación';
  toggle.setAttribute('aria-pressed', String(paused));
  updateMotion();
});
preference.addEventListener('change', updateMotion);
document.addEventListener('visibilitychange', updateMotion);
window.addEventListener('message', event => {
  if (event.source !== window.parent || event.origin !== window.location.origin) return;
  if (event.data?.type === 'show-evaluator') { visible = true; updateMotion(); }
  if (event.data?.type === 'hide-evaluator') { visible = false; updateMotion(); }
});
if (window.parent !== window) {
  document.querySelector('#return-link').hidden = true;
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') window.parent.postMessage({ type: 'close-evaluator' }, window.location.origin);
  });
}
updateMotion();
