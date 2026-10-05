/**
 * videoGuide.js
 * Lógica para la visualización del formato Video / Guion Didáctico Pedagógico.
 */

export const videoGuide = {
  elements: {},

  init() {
    this.elements = {
      videoTitle: document.getElementById('videoMockupTitle'),
      videoDuration: document.getElementById('videoDuration'),
      videoScriptList: document.getElementById('videoScriptList')
    };
  },

  render(videoData) {
    const { videoTitle, videoDuration, videoScriptList } = this.elements;
    if (!videoTitle || !videoScriptList) return;

    if (!videoData) {
      videoTitle.textContent = 'Tutorial Pedagógico';
      if (videoDuration) videoDuration.textContent = '4:00 min';
      videoScriptList.innerHTML = '<li>Guion didáctico en proceso de generación.</li>';
      return;
    }

    videoTitle.textContent = videoData.title || videoData.titulo_video || 'Tutorial Pedagógico';
    if (videoDuration) {
      videoDuration.textContent = videoData.duration || videoData.duracion || '4:30 min';
    }

    const items = videoData.key_points || videoData.puntos_video || [];
    videoScriptList.innerHTML = items.length > 0
      ? items.map(point => `<li>${point}</li>`).join('')
      : '<li>Estructura de guion generada por el agente pedagógico.</li>';
  }
};
