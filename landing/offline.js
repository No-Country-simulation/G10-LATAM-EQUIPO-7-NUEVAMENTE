// Fuentes: Data_IA/data/evaluation/results/retrieval_v2_ablation/*global_metrics.csv.
// Valores mostrados a tres decimales; comparación limitada al benchmark congelado.
const metrics = ['Recall@3', 'Recall@5', 'Precision@3', 'Precision@5'];
const baseline = [0.5733333333333333, 0.7533333333333333, 0.2133333333333333, 0.164];
const complete = [0.9333333333333333, 0.9533333333333333, 0.34, 0.208];
const variants = {
  unfiltered: { values: [0.8133333333333333, 0.8533333333333333, 0.3, 0.188], removed: ['filter'], title: 'El filtro reduce la competencia entre documentos.', finding: 'Sin document_id, Recall@5 baja de 0.953 a 0.853. Los casos sin evidencia relevante en Top-5 pasan de 2 a 7.', note: 'Se mantiene el retrieval híbrido y el Cross-Encoder; se elimina el filtro documental.' },
  vector: { values: [0.7833333333333333, 0.9033333333333333, 0.2866666666666666, 0.196], removed: ['bm25', 'rrf', 'cross'], title: 'La señal vectorial aporta cobertura; la combinación mejora el resultado.', finding: 'Solo Vector alcanza Recall@5 de 0.903. Vector + BM25 con RRF llega a 0.953 incluso antes del reranking.', note: 'Esta variante aísla una señal: no utiliza BM25, fusión ni Cross-Encoder.' },
  bm25: { values: [0.5033333333333333, 0.5733333333333333, 0.1866666666666667, 0.128], removed: ['vector', 'rrf', 'cross'], title: 'BM25 aislado tiene menor cobertura en este corpus.', finding: 'Recall@5 cae a 0.573. Su valor se observa como señal complementaria de la búsqueda vectorial, no como sustituto del pipeline completo.', note: 'Se conserva el filtro por documento y se utiliza únicamente el ranking léxico.' },
  rrf: { values: [0.8833333333333333, 0.9533333333333333, 0.32, 0.208], removed: ['cross'], title: 'El reranking mejora las primeras posiciones.', finding: 'Sin Cross-Encoder, Recall@5 se mantiene en 0.953, pero Recall@3 baja a 0.883 y Precision@3 a 0.320.', note: 'El mismo candidate pool llega a RRF; la selección final usa el ranking fusionado sin reranking.' },
  weighted: { values: [0.8433333333333333, 0.98, 0.3066666666666666, 0.216], removed: ['cross'], weighted: true, title: 'Más cobertura Top-5 no implica mejor ranking temprano.', finding: 'RRF 60/40 sin Cross-Encoder alcanza Recall@5 de 0.980, pero Recall@3 baja a 0.843. Frente a RRF 50/50 sin Cross, pasa de 0.883 a 0.843.', note: 'Pesos Vector/BM25: 60/40. La tabla compara con V2 completo; para aislar el peso, la referencia es RRF 50/50 sin Cross-Encoder.' },
  weightedCross: { values: [0.9133333333333333, 0.9333333333333333, 0.3333333333333333, 0.204], removed: [], weighted: true, title: 'La mejora aislada no se conserva con Cross-Encoder.', finding: 'Con reranking, RRF 60/40 queda por debajo de V2 completo en las cuatro métricas. Se mantiene la recomendación de pesos iguales, 50/50.', note: 'Aquí solo cambian los pesos de fusión: filtro, señales y Cross-Encoder se mantienen.' }
};

const chart = document.querySelector('#benchmark-chart');
metrics.forEach((metric, index) => {
  const card = document.createElement('article');
  card.className = 'metric';
  const title = document.createElement('h3');
  title.textContent = metric;
  card.append(title);
  [baseline[index], complete[index]].forEach((value, series) => {
    const row = document.createElement('div');
    row.className = 'bar-row';
    const label = document.createElement('span');
    label.textContent = series ? 'V2' : 'V1';
    const track = document.createElement('span');
    track.className = 'track';
    track.setAttribute('aria-hidden', 'true');
    const bar = document.createElement('span');
    bar.className = series ? 'bar v2' : 'bar';
    bar.style.width = value * 100 + '%';
    track.append(bar);
    const number = document.createElement('strong');
    number.textContent = value.toFixed(3);
    row.append(label, track, number);
    card.append(row);
  });
  chart.append(card);
});

function renderVariant() {
  const variant = variants[document.querySelector('#variant').value];
  document.querySelectorAll('[data-piece]').forEach(piece => {
    piece.classList.toggle('removed', variant.removed.includes(piece.dataset.piece));
    piece.classList.toggle('modified', piece.dataset.piece === 'rrf' && Boolean(variant.weighted));
    if (piece.dataset.piece === 'rrf') piece.textContent = variant.weighted ? 'RRF 60/40' : 'RRF 50/50';
  });
  const body = document.querySelector('#ablation-metrics');
  body.replaceChildren();
  metrics.forEach((metric, index) => {
    const row = document.createElement('tr');
    const delta = variant.values[index] - complete[index];
    const values = [metric, complete[index].toFixed(3), variant.values[index].toFixed(3), (delta > 0.00001 ? '+' : '') + delta.toFixed(3)];
    values.forEach((value, column) => {
      const cell = document.createElement(column ? 'td' : 'th');
      if (!column) cell.scope = 'row';
      cell.textContent = value;
      if (column === 3 && Math.abs(delta) > 0.00001) cell.className = delta > 0 ? 'positive' : 'negative';
      row.append(cell);
    });
    body.append(row);
  });
  document.querySelector('#finding-title').textContent = variant.title;
  document.querySelector('#finding').textContent = variant.finding;
  document.querySelector('#variant-note').textContent = variant.note;
}
document.querySelector('#variant').addEventListener('change', renderVariant);
renderVariant();

const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
const toggle = document.querySelector('#motion');
let paused = false;
let visible = true;
let view = 'architecture';
function updateMotion() {
  document.body.classList.toggle('paused', paused || !visible || document.hidden || preference.matches || view !== 'architecture');
  toggle.hidden = preference.matches || view !== 'architecture';
}
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
  view = button.dataset.view;
  document.querySelectorAll('[data-view]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  document.querySelectorAll('.view').forEach(panel => { panel.hidden = panel.id !== view; });
  updateMotion();
}));
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
  if (event.data?.type === 'show-offline') { visible = true; updateMotion(); }
  if (event.data?.type === 'hide-offline') { visible = false; updateMotion(); }
});
if (window.parent !== window) {
  document.querySelector('#return-link').hidden = true;
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') window.parent.postMessage({ type: 'close-offline' }, window.location.origin);
  });
}
updateMotion();
