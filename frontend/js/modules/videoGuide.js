/**
 * videoGuide.js
 * Lógica para la visualización del formato Guion Audiovisual Formativo (Video Script) RAG.
 * Contrato canónico Backend PR #71 (VideoScriptContentResponse: title, estimated_duration_minutes, scenes).
 * Manejo de estados (processing, pending, failed, no_results, success) y regeneración individual.
 */

import { toFriendlyError } from '../utils/friendlyError.js';

export const videoGuide = {
  elements: {},
  meta: {
    status: 'success',
    errorMessage: null,
    formatId: null
  },

  init() {
    this.elements = {
      videoTitle: document.getElementById('videoMockupTitle'),
      videoDuration: document.getElementById('videoDuration'),
      videoScriptList: document.getElementById('videoScriptList'),
      counterBadge: document.getElementById('videoCounterBadge'),
      btnRegen: document.getElementById('btnRegenVideo'),
      playBtn: document.getElementById('videoPlayPreviewBtn')
    };

    if (this.elements.btnRegen) {
      this.elements.btnRegen.addEventListener('click', () => {
        import('./studyHub.js').then(({ studyHub }) => {
          studyHub.triggerRegeneration(['video_script']);
        });
      });
    }

    if (this.elements.playBtn) {
      this.elements.playBtn.addEventListener('click', () => {
        // Enfoque a las escenas
        if (this.elements.videoScriptList) {
          this.elements.videoScriptList.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    }
  },

  render(videoData) {
    const { videoTitle, videoDuration, videoScriptList, counterBadge, btnRegen } = this.elements;
    if (!videoTitle || !videoScriptList) return;

    this.meta = {
      status: videoData?.status || (videoData ? 'success' : 'empty'),
      errorMessage: videoData?.error_message || null,
      formatId: videoData?.format_id || null
    };

    const isBusy = this.meta.status === 'processing' || this.meta.status === 'pending';
    if (btnRegen) {
      btnRegen.disabled = isBusy;
    }

    // Caso 1: En procesamiento o pendiente en el servidor
    if (isBusy) {
      if (counterBadge) counterBadge.textContent = 'Generando...';
      videoTitle.textContent = 'Generando Guion Audiovisual...';
      if (videoDuration) videoDuration.textContent = 'En proceso';

      videoScriptList.innerHTML = '';
      const noticeBox = document.createElement('div');
      noticeBox.style.textAlign = 'center';
      noticeBox.style.padding = '2rem 1rem';
      noticeBox.style.color = 'var(--text-secondary)';

      const pMsg = document.createElement('p');
      pMsg.style.fontSize = '0.95rem';
      pMsg.style.marginBottom = '0.5rem';
      pMsg.textContent = 'El pipeline de IA está estructurando las escenas, puestas en pantalla y locuciones didácticas a partir del documento indexado.';

      const spanAdvice = document.createElement('span');
      spanAdvice.style.fontSize = '0.8rem';
      spanAdvice.style.color = 'var(--accent-cyan)';
      spanAdvice.textContent = 'Por favor espera unos instantes.';

      noticeBox.appendChild(pMsg);
      noticeBox.appendChild(spanAdvice);
      videoScriptList.appendChild(noticeBox);
      return;
    }

    // Caso 2: Fallo en la generación del formato
    if (this.meta.status === 'failed') {
      const friendly = toFriendlyError({ message: this.meta.errorMessage });
      if (counterBadge) counterBadge.textContent = 'Guion (Fallo)';
      videoTitle.textContent = 'Guion Audiovisual No Disponible';
      if (videoDuration) videoDuration.textContent = 'Error';

      videoScriptList.innerHTML = '';
      const noticeCard = document.createElement('div');
      noticeCard.className = 'format-friendly-notice';

      const iconEl = document.createElement('div');
      iconEl.className = 'friendly-notice-icon';
      iconEl.textContent = '⚠️';

      const titleEl = document.createElement('h4');
      titleEl.className = 'friendly-notice-title';
      titleEl.textContent = friendly.title || 'Error al Generar Guion';

      const textEl = document.createElement('p');
      textEl.className = 'friendly-notice-text';
      textEl.textContent = friendly.message || 'La IA no pudo completar la estructura del guion audiovisual. Puedes solicitar un nuevo intento.';

      const actionsEl = document.createElement('div');
      actionsEl.className = 'friendly-notice-actions';

      const btnRetry = document.createElement('button');
      btnRetry.type = 'button';
      btnRetry.className = 'btn-friendly-action';
      const retrySpan = document.createElement('span');
      retrySpan.textContent = 'Reintentar Guion';
      btnRetry.appendChild(retrySpan);
      btnRetry.addEventListener('click', () => {
        import('./studyHub.js').then(({ studyHub }) => {
          studyHub.triggerRegeneration(['video_script']);
        });
      });

      actionsEl.appendChild(btnRetry);
      noticeCard.appendChild(iconEl);
      noticeCard.appendChild(titleEl);
      noticeCard.appendChild(textEl);
      noticeCard.appendChild(actionsEl);

      videoScriptList.appendChild(noticeCard);
      return;
    }

    // Caso 3: Sin contenido o sin resultados
    if (this.meta.status === 'no_results' || !videoData) {
      if (counterBadge) counterBadge.textContent = 'Guion Didáctico';
      videoTitle.textContent = 'Guion de Capacitación';
      if (videoDuration) videoDuration.textContent = '0:00';

      videoScriptList.innerHTML = '';
      const p = document.createElement('p');
      p.style.textAlign = 'center';
      p.style.padding = '1.5rem';
      p.style.color = 'var(--text-secondary)';
      p.textContent = 'El documento no contiene suficiente información para estructurar un guion audiovisual.';
      videoScriptList.appendChild(p);
      return;
    }

    // Caso 4: Éxito (Soporta content canónico anidado o plano)
    const content = videoData.content || videoData;
    const title = content.title || content.titulo_video || 'Guion de Capacitación';
    const durationMin = content.estimated_duration_minutes ?? content.duration_minutes;
    const durationText = durationMin != null
      ? `${durationMin}:00 min`
      : (content.duration || content.duracion || '4:30 min');

    if (counterBadge) counterBadge.textContent = 'Guion Audiovisual Formativo';
    videoTitle.textContent = title;
    if (videoDuration) videoDuration.textContent = durationText;

    videoScriptList.innerHTML = '';

    // A. Contrato canónico: Arreglo de escenas estructuradas
    const scenes = Array.isArray(content.scenes) ? content.scenes : [];
    if (scenes.length > 0) {
      scenes.forEach((scene, idx) => {
        const item = document.createElement('div');
        item.className = 'video-scene-item';

        const header = document.createElement('div');
        header.className = 'video-scene-header';

        const titleWrap = document.createElement('div');
        titleWrap.className = 'video-scene-title-wrap';

        const badge = document.createElement('span');
        badge.className = 'video-scene-badge';
        const sceneNum = scene.scene_id != null ? String(scene.scene_id) : String(idx + 1);
        badge.textContent = sceneNum.toLowerCase().startsWith('escena') ? sceneNum : `Escena ${sceneNum}`;

        const strongTitle = document.createElement('strong');
        strongTitle.className = 'video-scene-title';
        strongTitle.textContent = scene.title || `Bloque ${idx + 1}`;

        titleWrap.appendChild(badge);
        titleWrap.appendChild(strongTitle);

        const durSpan = document.createElement('span');
        durSpan.className = 'video-scene-duration';
        durSpan.textContent = scene.duration_seconds != null ? `${scene.duration_seconds} seg` : '';

        header.appendChild(titleWrap);
        header.appendChild(durSpan);

        item.appendChild(header);

        if (scene.visual_description) {
          const cue = document.createElement('div');
          cue.className = 'video-scene-cue';

          const cueLabel = document.createElement('strong');
          cueLabel.textContent = '🎬 Puesta en Pantalla:';

          const cueText = document.createTextNode(` ${scene.visual_description}`);

          cue.appendChild(cueLabel);
          cue.appendChild(cueText);
          item.appendChild(cue);
        }

        if (scene.narration) {
          const narration = document.createElement('div');
          narration.className = 'video-scene-narration';

          const narrationLabel = document.createElement('strong');
          narrationLabel.textContent = '🎙️ Locución / Guion:';

          const narrationText = document.createTextNode(` "${scene.narration}"`);

          narration.appendChild(narrationLabel);
          narration.appendChild(narrationText);
          item.appendChild(narration);
        }

        videoScriptList.appendChild(item);
      });
      return;
    }

    // B. Soporte fallback si no vinieron escenas pero sí key_points
    const items = content.key_points || content.puntos_video || [];
    if (items.length > 0) {
      const ul = document.createElement('ul');
      ul.style.paddingLeft = '1.25rem';
      ul.style.display = 'flex';
      ul.style.flexDirection = 'column';
      ul.style.gap = '0.65rem';

      items.forEach(point => {
        const li = document.createElement('li');
        li.style.fontSize = '0.9rem';
        li.style.color = 'var(--text-secondary)';
        li.style.lineHeight = '1.5';
        li.textContent = typeof point === 'string' ? point : String(point ?? '');
        ul.appendChild(li);
      });

      videoScriptList.appendChild(ul);
    } else {
      const p = document.createElement('p');
      p.style.fontSize = '0.9rem';
      p.style.color = 'var(--text-secondary)';
      p.textContent = 'Estructura formativa preparada para facilitadores y colaboradores.';
      videoScriptList.appendChild(p);
    }
  }
};
