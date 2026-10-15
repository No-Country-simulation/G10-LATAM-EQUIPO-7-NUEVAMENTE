const scenes = [...document.querySelectorAll('.scene')];
const sceneLinks = [...document.querySelectorAll('.deck-footer nav a')];
const previousScene = document.querySelector('#previous-scene');
const nextScene = document.querySelector('#next-scene');
const positionLabel = document.querySelector('#scene-position');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let sceneIndex = 0;
let playbackTimer = null;
let currentMode = 'general';
let stepIndex = 0;
let fitFrame = null;
let entranceFrame = null;
let entranceAnimations = [];

function stopEntranceAnimations() {
  if (entranceFrame !== null) window.cancelAnimationFrame(entranceFrame);
  entranceFrame = null;
  entranceAnimations.forEach((animation) => animation.cancel());
  entranceAnimations = [];
}

function animateSceneEntrance(scene) {
  stopEntranceAnimations();
  if (reducedMotion.matches || typeof scene.animate !== 'function') return;
  entranceFrame = window.requestAnimationFrame(() => {
    entranceFrame = null;
    const animate = (element, frames, options) => {
      entranceAnimations.push(element.animate(frames, options));
    };
    const reveal = (selector, start = 0, stagger = 65) => {
      scene.querySelectorAll(selector).forEach((element, index) => {
        animate(element, [
          { opacity: 0, transform: 'scale(0.98)' },
          { opacity: 1, transform: 'scale(1)' }
        ], { duration: 430, delay: start + index * stagger, easing: 'cubic-bezier(.2,.75,.25,1)', fill: 'backwards' });
      });
    };
    reveal('.scene-heading, .demo-copy, .architecture-heading', 0);
    if (scene.id === 'documento') {
      reveal('.source-document', 100);
      reveal('.audience', 260, 90);
      const connections = scene.querySelector('.audience-lines path');
      if (connections && typeof connections.getTotalLength === 'function') {
        const length = connections.getTotalLength();
        animate(connections, [
          { strokeDasharray: String(length), strokeDashoffset: String(length), opacity: 0 },
          { strokeDasharray: String(length), strokeDashoffset: '0', opacity: 1 }
        ], { duration: 850, delay: 100, easing: 'ease-out', fill: 'backwards' });
      }
    } else if (scene.id === 'transformacion') {
      reveal('.transformation-line > *', 100, 75);
      reveal('.output-connector', 400);
      reveal('.format-grid article', 450, 80);
    } else if (scene.id === 'demo') {
      reveal('.journey-heading', 100);
      reveal('.demo-journey li', 180, 140);
      reveal('.journey-note', 600);
    } else if (scene.id === 'arquitectura') {
      reveal('.system-canvas', 100);
      reveal('.sequence-bar, .architecture-footer', 240, 90);
    } else if (scene.id === 'equipo') {
      reveal('.person-card', 100, 55);
      reveal('.contributors', 550);
    } else if (scene.id === 'impacto') {
      reveal('.impact-grid article', 140, 120);
      reveal('.team-strip, .closing-links', 500, 100);
    }
    reveal('.scene-foot', 600);
  });
}

function fitCurrentScene() {
  fitFrame = null;
  const scene = scenes[sceneIndex];
  scene.style.zoom = '';
  if (!window.matchMedia('(min-width: 761px)').matches) return;
  const deck = document.querySelector('#deck');
  const availableHeight = deck.clientHeight - 4;
  const availableWidth = deck.clientWidth - 4;
  if (availableHeight <= 0 || availableWidth <= 0) return;
  let scale = 1;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const bounds = scene.getBoundingClientRect();
    const renderedHeight = Math.max(bounds.height, scene.scrollHeight * scale);
    const renderedWidth = Math.max(bounds.width, scene.scrollWidth * scale);
    const adjustment = Math.min(1, availableHeight / renderedHeight, availableWidth / renderedWidth);
    if (adjustment >= 0.999) break;
    scale *= adjustment;
    scene.style.zoom = String(scale);
  }
}

function scheduleSceneFit() {
  if (fitFrame !== null) window.cancelAnimationFrame(fitFrame);
  fitFrame = window.requestAnimationFrame(fitCurrentScene);
}

const descriptions = {
  frontend: 'Frontend: carga de documentos, consulta de formatos y experiencia de aprendizaje.',
  backend: 'BackendAPI: coordina servicios, conserva resultados y controla las decisiones y reintentos.',
  rag: 'Investigador RAG: recupera del documento la evidencia necesaria para cada formato.',
  writer: 'Redactor Pedagógico: genera o corrige el contenido según el contexto de aprendizaje.',
  reviewer: 'Agente Revisor: interpreta recomendaciones y decide si necesita nueva evidencia.',
  evaluator: 'Data/IA: evalúa relevancia, coherencia, adaptación didáctica y respaldo documental.'
};
const nodes = [...document.querySelectorAll('[data-node]')];
const edges = [...document.querySelectorAll('.edges path')];
const evidenceCheckbox = document.querySelector('#new-evidence');
const playButton = document.querySelector('#step-play');
const pauseButton = document.querySelector('#step-pause');
const stepCount = document.querySelector('#step-count');
const stepDescription = document.querySelector('#step-description');
const resourcesDialog = document.querySelector('#resources-dialog');

function getSteps() {
  const generation = [
      { node: 'frontend', text: 'Frontend solicita contenido para un documento y un contexto pedagógico.' },
      { node: 'backend', edge: 'front-back', text: 'BackendAPI recibe la solicitud y coordina la generación.' },
      { node: 'rag', edge: 'back-rag', text: 'El Investigador RAG recupera la evidencia relevante del documento.' },
      { node: 'writer', edge: 'rag-writer', text: 'El Redactor transforma la evidencia en contenido educativo adaptado.' },
      { node: 'backend', edge: 'writer-back', text: 'BackendAPI recibe y conserva el contenido junto con la evidencia utilizada.' },
      { node: 'evaluator', edge: 'back-eval', text: 'Data/IA evalúa el contenido, su contexto pedagógico y su respaldo documental.' },
      { node: 'backend', edge: 'eval-back', text: 'BackendAPI recibe la evaluación y decide si acepta el contenido o solicita corrección.' }
    ].map((step) => ({ ...step, phase: 'GENERACIÓN Y EVALUACIÓN' }));
  const steps = [
    { node: 'backend', text: 'Si la evaluación requiere ajustes y quedan intentos, BackendAPI solicita corregir.' },
    { node: 'reviewer', edge: 'back-reviewer', text: 'El Revisor interpreta las recomendaciones y decide cómo corregir.' }
  ];
  if (evidenceCheckbox.checked) {
    steps.push({ node: 'rag', edge: 'reviewer-rag', text: 'Hace falta información: el Investigador RAG recupera evidencia adicional.' });
  }
  steps.push(
    { node: 'writer', edge: evidenceCheckbox.checked ? 'rag-writer' : 'reviewer-writer', text: 'El Redactor produce una versión corregida con la evidencia disponible.' },
    { node: 'backend', edge: 'writer-back', text: 'BackendAPI recibe la nueva versión y conserva el historial del proceso.' },
    { node: 'evaluator', edge: 'back-eval', text: 'Data/IA evalúa nuevamente el contenido corregido.' },
    { node: 'backend', edge: 'eval-back', text: 'El ciclo termina al aprobar el contenido o alcanzar el límite de correcciones.' }
  );
  return generation.concat(
    steps.map((step) => ({ ...step, phase: 'CORRECCIÓN Y REEVALUACIÓN' })),
    { node: 'frontend', edge: 'back-front', phase: 'RESPUESTA AL USUARIO', text: 'BackendAPI devuelve al Frontend el contenido final y el historial de evaluaciones para su consulta.' }
  );
}

function stopPlayback() {
  window.clearInterval(playbackTimer);
  playbackTimer = null;
  playButton.disabled = false;
  pauseButton.disabled = true;
  document.querySelector('.system-canvas').classList.remove('playing');
}

function highlightNode(nodeId, edgeId) {
  nodes.forEach((node) => node.classList.toggle('active', node.dataset.node === nodeId));
  edges.forEach((edge) => {
    edge.classList.toggle('active', edge.id === 'edge-' + edgeId);
    edge.classList.toggle('dimmed', currentMode !== 'general' && edge.id !== 'edge-' + edgeId);
  });
  document.querySelector('#agent-boundary').classList.toggle('active', ['rag', 'writer', 'reviewer'].includes(nodeId));
}

function renderStep() {
  const steps = getSteps();
  const step = steps[stepIndex];
  highlightNode(step.node, step.edge);
  stepCount.textContent = step.phase + ' · PASO ' + (stepIndex + 1) + ' / ' + steps.length;
  stepDescription.textContent = step.text;
  if (stepIndex === steps.length - 1) stopPlayback();
  scheduleSceneFit();
}

function resetSequence() {
  stopPlayback();
  currentMode = 'general';
  stepIndex = -1;
  highlightNode(null, null);
  stepCount.textContent = 'EL SISTEMA';
  stepDescription.textContent = 'Reproduce el recorrido completo: generación, evaluación y un caso que requiere corrección.';
  scheduleSceneFit();
}

function showScene(index, focusHeading = false) {
  stopPlayback();
  sceneIndex = Math.max(0, Math.min(index, scenes.length - 1));
  scenes.forEach((scene, position) => { scene.hidden = position !== sceneIndex; });
  sceneLinks.forEach((link, position) => {
    if (position === sceneIndex) link.setAttribute('aria-current', 'step');
    else link.removeAttribute('aria-current');
  });
  previousScene.disabled = sceneIndex === 0;
  nextScene.disabled = sceneIndex === scenes.length - 1;
  positionLabel.textContent = String(sceneIndex + 1).padStart(2, '0') + ' / ' + String(scenes.length).padStart(2, '0');
  window.scrollTo({ top: 0, behavior: 'instant' });
  if (focusHeading) scenes[sceneIndex].querySelector('h1, h2').focus({ preventScroll: true });
  scheduleSceneFit();
  animateSceneEntrance(scenes[sceneIndex]);
}

function navigateTo(index) {
  if (index < 0 || index >= scenes.length) return;
  const hash = '#' + scenes[index].id;
  if (window.location.hash === hash) showScene(index, true);
  else window.location.hash = hash;
}

window.addEventListener('hashchange', () => {
  const index = scenes.findIndex((scene) => '#' + scene.id === window.location.hash);
  showScene(index < 0 ? 0 : index, true);
});
previousScene.addEventListener('click', () => navigateTo(sceneIndex - 1));
nextScene.addEventListener('click', () => navigateTo(sceneIndex + 1));
document.addEventListener('keydown', (event) => {
  if (resourcesDialog.open || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (event.target.closest('button, a, input, select, textarea, [role="button"]')) return;
  if (['ArrowRight', 'PageDown', 'ArrowLeft', 'PageUp', 'Home', 'End'].includes(event.key)) {
    event.preventDefault();
    if (event.key === 'Home') navigateTo(0);
    else if (event.key === 'End') navigateTo(scenes.length - 1);
    else navigateTo(sceneIndex + (['ArrowRight', 'PageDown'].includes(event.key) ? 1 : -1));
  }
});

evidenceCheckbox.addEventListener('change', resetSequence);
document.querySelector('#step-reset').addEventListener('click', resetSequence);
pauseButton.addEventListener('click', stopPlayback);
playButton.addEventListener('click', () => {
  if (playbackTimer !== null) return;
  currentMode = 'process';
  if (stepIndex < 0 || stepIndex === getSteps().length - 1) stepIndex = 0;
  renderStep();
  playButton.disabled = true;
  pauseButton.disabled = false;
  document.querySelector('.system-canvas').classList.add('playing');
  playbackTimer = window.setInterval(() => {
    stepIndex = Math.min(stepIndex + 1, getSteps().length - 1);
    renderStep();
  }, 2600);
});
nodes.forEach((node) => {
  function inspectNode() {
    resetSequence();
    highlightNode(node.dataset.node, null);
    stepCount.textContent = 'RESPONSABILIDAD';
    stepDescription.textContent = descriptions[node.dataset.node];
    scheduleSceneFit();
  }
  node.addEventListener('click', inspectNode);
  node.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inspectNode(); }
  });
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { stopPlayback(); stopEntranceAnimations(); }
});
reducedMotion.addEventListener('change', () => { stopPlayback(); stopEntranceAnimations(); });

const openResources = document.querySelector('#open-resources');
if (typeof resourcesDialog.showModal === 'function') {
  openResources.hidden = false;
  openResources.addEventListener('click', () => { stopPlayback(); resourcesDialog.showModal(); });
  document.querySelector('#close-resources').addEventListener('click', () => resourcesDialog.close());
  resourcesDialog.addEventListener('click', (event) => { if (event.target === resourcesDialog) resourcesDialog.close(); });
}
const fullscreenButton = document.querySelector('.fullscreen');
if (document.fullscreenEnabled) {
  fullscreenButton.hidden = false;
  fullscreenButton.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      fullscreenButton.textContent = 'Pantalla completa no disponible';
    }
  });
  document.addEventListener('fullscreenchange', () => {
    fullscreenButton.textContent = document.fullscreenElement ? 'Salir de pantalla completa ↙' : 'Pantalla completa ↗';
  });
}

document.body.classList.add('enhanced');
previousScene.hidden = false;
nextScene.hidden = false;
document.querySelector('.architecture-toolbar').hidden = false;
const initialIndex = scenes.findIndex((scene) => '#' + scene.id === window.location.hash);
showScene(initialIndex < 0 ? 0 : initialIndex);
resetSequence();
window.addEventListener('resize', scheduleSceneFit);
document.addEventListener('fullscreenchange', scheduleSceneFit);
window.addEventListener('load', scheduleSceneFit);
if (window.visualViewport) window.visualViewport.addEventListener('resize', scheduleSceneFit);
if (document.fonts) document.fonts.ready.then(scheduleSceneFit);
