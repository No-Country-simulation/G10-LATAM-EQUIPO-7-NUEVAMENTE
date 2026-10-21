const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
let entranceAnimations = [];
let diagramVisible = true;
let motionPaused = false;
const motionToggle = document.createElement('button');
motionToggle.type = 'button';
motionToggle.className = 'motion-toggle';
motionToggle.textContent = 'Pausar animación';
motionToggle.setAttribute('aria-pressed', 'false');
document.querySelector('.note').append(document.createElement('br'), motionToggle);
motionToggle.addEventListener('click', () => {
  motionPaused = !motionPaused;
  motionToggle.textContent = motionPaused ? 'Reanudar animación' : 'Pausar animación';
  motionToggle.setAttribute('aria-pressed', String(motionPaused));
  animateDiagram();
});

function stopEntrance() {
  entranceAnimations.forEach((animation) => animation.cancel());
  entranceAnimations = [];
}

function animateDiagram() {
  stopEntrance();
  motionToggle.hidden = motionPreference.matches;
  if (motionPreference.matches || motionPaused || !diagramVisible || document.hidden || typeof document.body.animate !== 'function') return;
  const stages = ['.input', '.semantic, .lexical', '.fusion', '.rerank', '.output'];
  stages.forEach((selector, index) => {
    document.querySelectorAll(selector).forEach((element) => {
      entranceAnimations.push(element.querySelector('rect').animate([
        { strokeOpacity: .65, offset: 0 },
        { strokeOpacity: 1, offset: .12 },
        { strokeOpacity: .65, offset: .3 },
        { strokeOpacity: .65, offset: 1 }
      ], {
        duration: 10000, delay: index * 1600, iterations: Infinity, easing: 'ease-in-out'
      }));
    });
  });
  document.querySelectorAll('.wires path').forEach((path, index) => {
    entranceAnimations.push(path.animate([
      { stroke: '#54718e', strokeDashoffset: '0', offset: 0 },
      { stroke: '#7dd3fc', strokeDashoffset: '-12', offset: .15 },
      { stroke: '#54718e', strokeDashoffset: '-24', offset: .35 },
      { stroke: '#54718e', strokeDashoffset: '-72', offset: 1 }
    ], { duration: 10000, delay: [400, 400, 2000, 2000, 3600, 5200][index], iterations: Infinity, easing: 'linear' }));
  });
}

motionPreference.addEventListener('change', animateDiagram);
document.addEventListener('visibilitychange', animateDiagram);
window.addEventListener('message', (event) => {
  if (event.source !== window.parent || event.origin !== window.location.origin) return;
  if (event.data?.type === 'show-rag') { diagramVisible = true; animateDiagram(); }
  if (event.data?.type === 'hide-rag') { diagramVisible = false; stopEntrance(); }
});
animateDiagram();

if (window.parent !== window) {
  document.querySelector('#return-link').hidden = true;
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') window.parent.postMessage({ type: 'close-rag' }, window.location.origin);
  });
}
