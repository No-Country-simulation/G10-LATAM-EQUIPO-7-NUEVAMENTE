const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const motion = document.querySelector('#motion');
let scenario = 'direct';
let paused = false;
let visible = true;
let timer = null;
let stage = 0;

function updateMotion() {
  window.clearInterval(timer);
  const stopped = paused || !visible || document.hidden || reducedMotion.matches;
  document.body.classList.toggle('paused', stopped);
  motion.hidden = reducedMotion.matches;
  document.querySelectorAll('.stage').forEach(node => node.classList.remove('current'));
  if (stopped) return;
  const route = ['inspect', 'decide', ...(scenario === 'evidence' ? ['retrieve'] : []), 'rewrite', 'deliver'];
  const advance = () => {
    document.querySelectorAll('.stage').forEach(node => node.classList.toggle('current', node.classList.contains(route[stage % route.length])));
    stage += 1;
  };
  advance();
  timer = window.setInterval(advance, 2200);
}

function selectScenario(value) {
  scenario = value;
  stage = 0;
  document.querySelectorAll('[data-case]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.case === value)));
  for (const branch of ['direct', 'evidence']) {
    document.querySelectorAll('.route-' + branch).forEach(node => node.classList.toggle('muted', branch !== value));
  }
  document.querySelectorAll('.wires path').forEach(path => path.classList.toggle('selected', !path.classList.contains('muted')));
  document.querySelector('#case-label').textContent = value === 'direct' ? 'EJEMPLO · Ajuste didáctico' : 'EJEMPLO · Falta de respaldo documental';
  document.querySelector('#case-title').textContent = value === 'direct' ? '«Simplificar el lenguaje para el perfil destinatario»' : '«Una afirmación necesita mayor sustento en la fuente»';
  document.querySelector('#case-description').textContent = value === 'direct'
    ? 'el Revisor puede enviar el feedback directamente al Redactor utilizando la evidencia disponible.'
    : 'el Revisor solicita evidencia adicional del mismo documento antes de enviarla al Redactor.';
  updateMotion();
}
document.querySelectorAll('[data-case]').forEach(button => button.addEventListener('click', () => selectScenario(button.dataset.case)));
motion.addEventListener('click', () => {
  paused = !paused;
  motion.textContent = paused ? 'Reanudar animación' : 'Pausar animación';
  motion.setAttribute('aria-pressed', String(paused));
  updateMotion();
});
reducedMotion.addEventListener('change', updateMotion);
document.addEventListener('visibilitychange', updateMotion);
window.addEventListener('message', event => {
  if (event.source !== window.parent || event.origin !== window.location.origin) return;
  if (event.data?.type === 'show-reviewer') { visible = true; updateMotion(); }
  if (event.data?.type === 'hide-reviewer') { visible = false; updateMotion(); }
});
if (window.parent !== window) {
  document.querySelector('#return-link').hidden = true;
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') window.parent.postMessage({ type: 'close-reviewer' }, window.location.origin);
  });
}
selectScenario('direct');
