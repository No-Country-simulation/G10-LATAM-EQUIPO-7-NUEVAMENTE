/**
 * videoGuide.js
 * Visualización del formato Guion Formativo / Video Script (PR #71 BackendAPI).
 * Soporta contrato oficial VideoScriptContentResponse { title, estimated_duration_minutes, scenes }.
 */

import { toFriendlyError } from '../utils/friendlyError.js';

export const videoGuide = {
  elements: {},
  videoMeta: null,

  init() {
    this.elements = {
      mainContent: document.getElementById('videoMainContent'),
      noticeContainer: document.getElementById('videoNoticeContainer'),
      counterBadge: document.getElementById('videoCounterBadge'),
      btnRegenVideo: document.getElementById('btnRegenVideo'),
      videoTitle: document.getElementById('videoMockupTitle'),
      videoDuration: document.getElementById('videoDuration'),
      videoScriptList: document.getElementById('videoScriptList'),
      videoScriptBoxTitle: document.getElementById('videoScriptBoxTitle')
    };

    if (this.elements.btnRegenVideo) {
      this.elements.btnRegenVideo.addEventListener('click', () => {
        import('./studyHub.js').then(({ studyHub }) => {
          studyHub.triggerRegeneration(['video_script']);
        });
      });
    }
  },

  render(videoData) {
    const {
      mainContent, noticeContainer, counterBadge, btnRegenVideo,
      videoTitle, videoDuration, videoScriptList, videoScriptBoxTitle
    } = this.elements;

    if (!mainContent) return;

    this.videoMeta = {
      status: videoData?.status || (videoData?.content ? 'success' : (videoData ? 'success' : 'empty')),
      errorMessage: videoData?.error_message || null,
      title: videoData?.content?.title || videoData?.title || null
    };

    if (btnRegenVideo) {
      const isBusy = this.videoMeta.status === 'processing' || this.videoMeta.status === 'pending';
      btnRegenVideo.disabled = isBusy;
    }

    if (counterBadge) {
      if (this.videoMeta.status === 'processing' || this.videoMeta.status === 'pending') {
        counterBadge.textContent = 'Generando Guion...';
      } else {
        counterBadge.textContent = 'Guion Audiovisual';
      }
    }

    // Manejo de Estados Especiales: failed, processing, pending, no_results o empty
    if (!videoData || this.videoMeta.status === 'failed' || this.videoMeta.status === 'processing' || this.videoMeta.status === 'pending' || this.videoMeta.status === 'no_results' || this.videoMeta.status === 'empty') {
      if (mainContent) mainContent.style.display = 'none';
      if (noticeContainer) {
        noticeContainer.style.display = 'block';
        noticeContainer.textContent = ''; // Limpieza segura

        if (this.videoMeta.status === 'failed') {
          const friendly = toFriendlyError({ message: this.videoMeta.errorMessage });
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const iconEl = document.createElement('div');
          iconEl.className = 'friendly-notice-icon';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = friendly.title || 'Guion No Disponible';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = friendly.message || 'No fue posible generar el guion formativo.';

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
          noticeContainer.appendChild(noticeCard);
        } else if (this.videoMeta.status === 'processing' || this.videoMeta.status === 'pending') {
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = 'Generando Guion Audiovisual...';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = 'El pipeline de IA está estructurando las escenas, locución y descripciones visuales del material indexado.';

          noticeCard.appendChild(titleEl);
          noticeCard.appendChild(textEl);
          noticeContainer.appendChild(noticeCard);
        } else if (this.videoMeta.status === 'no_results') {
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = 'Sin Guion Generado';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = 'El documento no contiene suficiente información para estructurar un guion de video.';

          noticeCard.appendChild(titleEl);
          noticeCard.appendChild(textEl);
          noticeContainer.appendChild(noticeCard);
        } else {
          const noticeCard = document.createElement('div');
          noticeCard.className = 'format-friendly-notice';

          const titleEl = document.createElement('h4');
          titleEl.className = 'friendly-notice-title';
          titleEl.textContent = 'Guion en Espera';

          const textEl = document.createElement('p');
          textEl.className = 'friendly-notice-text';
          textEl.textContent = 'El guion formativo se generará automáticamente a partir del material corporativo cargado.';

          noticeCard.appendChild(titleEl);
          noticeCard.appendChild(textEl);
          noticeContainer.appendChild(noticeCard);
        }
      }
      return;
    }

    // Estado Exitoso: Renderizado de datos del contrato oficial (PR #71)
    if (noticeContainer) noticeContainer.style.display = 'none';
    if (mainContent) mainContent.style.display = 'grid';

    const content = videoData.content || videoData;
    const title = content.title || this.videoMeta.title || 'Guion de Capacitación';

    if (videoTitle) {
      videoTitle.textContent = title;
    }

    // Cálculo y formateo de duración
    const scenes = Array.isArray(content.scenes) ? content.scenes : [];
    let durationText = '3:00 min';

    if (typeof content.estimated_duration_minutes === 'number' && content.estimated_duration_minutes > 0) {
      durationText = `${content.estimated_duration_minutes}:00 min`;
    } else if (scenes.length > 0) {
      const totalSeconds = scenes.reduce((acc, s) => acc + (typeof s.duration_seconds === 'number' ? s.duration_seconds : 30), 0);
      const mins = Math.floor(totalSeconds / 60);
      const secs = totalSeconds % 60;
      durationText = `${mins}:${secs < 10 ? '0' : ''}${secs} min`;
    }

    if (videoDuration) {
      videoDuration.textContent = durationText;
    }

    if (videoScriptBoxTitle) {
      videoScriptBoxTitle.textContent = scenes.length > 0
        ? `Estructura del Guion (${scenes.length} ${scenes.length === 1 ? 'Escena' : 'Escenas'})`
        : 'Estructura del Guion Formativo';
    }

    // Renderizado seguro de las escenas (VideoScriptSceneResponse)
    if (videoScriptList) {
      videoScriptList.textContent = ''; // Limpieza segura

      if (scenes.length > 0) {
        scenes.forEach((scene, index) => {
          const card = document.createElement('div');
          card.className = 'video-scene-card';

          // Cabecera de la escena
          const header = document.createElement('div');
          header.className = 'scene-card-header';

          const sceneTitle = document.createElement('span');
          sceneTitle.className = 'scene-card-title';
          const sceneNum = index + 1;
          const rawSceneTitle = scene.title || `Escena ${sceneNum}`;
          sceneTitle.textContent = `${sceneNum}. ${rawSceneTitle}`;

          const durationBadge = document.createElement('span');
          durationBadge.className = 'scene-card-duration';
          const durSec = typeof scene.duration_seconds === 'number' ? `${scene.duration_seconds}s` : '30s';
          durationBadge.textContent = durSec;

          header.appendChild(sceneTitle);
          header.appendChild(durationBadge);
          card.appendChild(header);

          // Descripción Visual
          if (scene.visual_description) {
            const visualField = document.createElement('div');
            visualField.className = 'scene-card-field';

            const visualLabel = document.createElement('span');
            visualLabel.className = 'scene-field-label';
            visualLabel.textContent = '🎬 Descripción Visual:';

            const visualContent = document.createElement('div');
            visualContent.textContent = scene.visual_description;

            visualField.appendChild(visualLabel);
            visualField.appendChild(visualContent);
            card.appendChild(visualField);
          }

          // Locución / Narración
          if (scene.narration) {
            const narrationField = document.createElement('div');
            narrationField.className = 'scene-card-field';

            const narrationLabel = document.createElement('span');
            narrationLabel.className = 'scene-field-label';
            narrationLabel.textContent = '🎙️ Locución / Voz en Off:';

            const narrationBox = document.createElement('div');
            narrationBox.className = 'scene-narration-box';
            narrationBox.textContent = `"${scene.narration}"`;

            narrationField.appendChild(narrationLabel);
            narrationField.appendChild(narrationBox);
            card.appendChild(narrationField);
          }

          videoScriptList.appendChild(card);
        });
      } else {
        // Fallback si viene en formato plano de puntos
        const items = content.key_points || content.puntos_video || [];
        if (items.length > 0) {
          const ul = document.createElement('ul');
          items.forEach(point => {
            const li = document.createElement('li');
            li.textContent = typeof point === 'string' ? point : String(point ?? '');
            ul.appendChild(li);
          });
          videoScriptList.appendChild(ul);
        } else {
          const emptyMsg = document.createElement('p');
          emptyMsg.style.fontSize = '0.9rem';
          emptyMsg.style.color = 'var(--text-secondary)';
          emptyMsg.textContent = 'Estructura audiovisual procesada para facilitadores.';
          videoScriptList.appendChild(emptyMsg);
        }
      }
    }
  }
};
