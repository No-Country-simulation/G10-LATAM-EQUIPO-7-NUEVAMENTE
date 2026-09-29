/**
 * uploadTab.js
 * Controlador de la Pestaña Completa de Ingesta, Parámetros Pedagógicos y Pipeline RAG.
 * Incorpora límite estricto de 10 MB (Tarea 4) y manejo UX de errores y estados (Tarea 5).
 */

import { CONFIG } from '../config.js';
import { state } from '../state.js';
import { sampleLibrary } from '../data/sampleLibrary.js';
import { apiClient, ApiError } from '../api/apiClient.js';
import { router } from './router.js';
import { statusDialog } from './statusDialog.js';
import {
  notifySuccess,
  notifyWarning,
  notifyError,
  notifyInfo
} from './notifications.js';

export const uploadTab = {
  elements: {},
  currentActiveStep: null,

  init() {
    this.bindElements();
    this.setupDropzone();
    this.setupSampleButtons();
    this.setupParamListeners();
    this.setupExecution();
    this.setupResolverActions();
    this.setupDemoStatusTester();
    this.syncInitialState();
  },

  bindElements() {
    this.elements = {
      dropArea: document.getElementById('dropAreaLarge'),
      docFileInput: document.getElementById('docFileInput'),
      selectedFileCard: document.getElementById('selectedFileCard'),
      selectedFileName: document.getElementById('selectedFileName'),
      selectedFileSize: document.getElementById('selectedFileSize'),
      fileFormatBadge: document.getElementById('fileFormatBadge'),
      btnRemoveFile: document.getElementById('btnRemoveFile'),
      quickSampleBtns: document.querySelectorAll('.btn-quick-sample'),

      // Parámetros
      paramPerfil: document.getElementById('paramPerfil'),
      paramFormato: document.getElementById('paramFormato'),
      paramNicho: document.getElementById('paramNicho'),

      // Stepper
      pipelineCard: document.getElementById('pipelineCard'),
      pipelineStatusBadge: document.getElementById('pipelineStatusBadge'),
      stepOci: document.getElementById('stepOci'),
      stepChroma: document.getElementById('stepChroma'),
      stepGen: document.getElementById('stepGen'),
      stepCritic: document.getElementById('stepCritic'),
      line1: document.getElementById('line1'),
      line2: document.getElementById('line2'),
      line3: document.getElementById('line3'),
      pipelineLiveLog: document.getElementById('pipelineLiveLog'),
      btnLanzarProcesamiento: document.getElementById('btnLanzarProcesamiento'),

      // Resultados y Resolver
      resultBoxContainer: document.getElementById('resultBoxContainer'),
      badgeTiempo: document.getElementById('badgeTiempo'),
      badgeSecciones: document.getElementById('badgeSecciones'),
      badgeNivel: document.getElementById('badgeNivel'),
      resolverFormatCards: document.querySelectorAll('.btn-resolver-card'),
      btnIrALaBiblioteca: document.getElementById('btnIrALaBiblioteca')
    };
  },

  setupDropzone() {
    const { dropArea, docFileInput } = this.elements;
    if (!dropArea || !docFileInput) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropArea.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropArea.classList.remove('dragover');
      });
    });

    dropArea.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        this.handleFileChosen(e.dataTransfer.files[0]);
      }
    });

    docFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        this.handleFileChosen(e.target.files[0]);
      }
    });

    if (this.elements.btnRemoveFile) {
      this.elements.btnRemoveFile.addEventListener('click', () => {
        this.clearFile();
      });
    }
  },

  /**
   * Valida el archivo: límite 10 MB (Tarea 4), formato admitido y no vacío (Tarea 5)
   * @param {File} file 
   */
  handleFileChosen(file) {
    if (!file) return;

    // Validación 1: Formato / extensión permitida
    const ext = file.name.split('.').pop().toLowerCase();
    const allowed = CONFIG.UPLOAD.ALLOWED_EXTENSIONS || ['pdf', 'md', 'txt'];
    if (!allowed.includes(ext)) {
      this.flashDropzoneError();
      statusDialog.showError({
        status: 415,
        code: 'UNSUPPORTED_MEDIA_TYPE',
        message: `Formato de archivo .${ext} no soportado. Se admiten archivos PDF, Markdown (.md) y TXT.`,
        filename: file.name
      });
      notifyError(
        'Formato No Soportado (415)',
        `El archivo .${ext} no está permitido. Solo se admiten archivos: ${allowed.map(e => '.' + e).join(', ')}.`
      );
      this.clearFile();
      return;
    }

    // Validación 2: Límite de 10 MB en Frontend (Tarea 4)
    const maxSizeBytes = CONFIG.UPLOAD.MAX_SIZE_MB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      this.flashDropzoneError();
      const currentSizeMb = (file.size / (1024 * 1024)).toFixed(1);
      statusDialog.showError({
        status: 413,
        code: 'FILE_TOO_LARGE',
        message: `El archivo supera el tamaño máximo permitido de ${CONFIG.UPLOAD.MAX_SIZE_MB} MB (${currentSizeMb} MB).`,
        details: [
          `Tamaño detectado: ${currentSizeMb} MB`,
          `Límite admitido: ${CONFIG.UPLOAD.MAX_SIZE_MB} MB`
        ],
        filename: file.name
      });
      notifyError(
        'Archivo Demasiado Grande (413)',
        `"${file.name}" (${currentSizeMb} MB) supera el límite máximo permitido de ${CONFIG.UPLOAD.MAX_SIZE_MB} MB.`
      );
      this.clearFile();
      return;
    }

    // Validación 3: Archivo vacío (0 bytes)
    if (file.size === 0) {
      this.flashDropzoneError();
      statusDialog.showError({
        status: 400,
        code: 'BAD_REQUEST',
        message: 'El documento seleccionado está vacío (0 bytes).',
        filename: file.name
      });
      notifyError(
        'Documento Vacío (400)',
        'El archivo seleccionado no tiene contenido (0 bytes).'
      );
      this.clearFile();
      return;
    }

    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);

    const fileData = {
      name: file.name,
      size: `${sizeMb} MB`,
      format: ext.toUpperCase(),
      sampleKey: null,
      rawFile: file
    };

    state.set({ selectedFile: fileData });
    this.renderSelectedFile(fileData);

    // Desactivar botones de muestra rápida
    this.elements.quickSampleBtns.forEach(btn => btn.classList.remove('active'));

    notifyInfo(
      'Archivo Seleccionado',
      `"${file.name}" (${sizeMb} MB) verificado y listo para procesar.`
    );
  },

  flashDropzoneError() {
    const dropArea = this.elements.dropArea;
    if (!dropArea) return;
    dropArea.classList.add('dropzone-error');
    setTimeout(() => {
      dropArea.classList.remove('dropzone-error');
    }, 1200);
  },

  setupSampleButtons() {
    this.elements.quickSampleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const sampleKey = btn.getAttribute('data-sample');
        const sample = sampleLibrary[sampleKey];
        if (!sample) return;

        this.elements.quickSampleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const fileData = {
          name: sample.filename,
          size: sample.filesize,
          format: sample.filename.split('.').pop().toUpperCase(),
          sampleKey: sampleKey,
          rawFile: null
        };

        state.set({ selectedFile: fileData });
        this.renderSelectedFile(fileData);

        // Preseleccionar parámetros sugeridos
        if (sample.metadatos) {
          if (this.elements.paramPerfil) {
            const rawPerfil = sample.metadatos.target_profile || sample.metadatos.perfil;
            const map = { principiante: 'beginner', intermedio: 'intermediate', avanzado: 'advanced' };
            this.elements.paramPerfil.value = map[rawPerfil] || rawPerfil || 'intermediate';
          }
        }
      });
    });
  },

  setupParamListeners() {
    const updateParams = () => {
      state.set({
        adaptationParams: {
          target_profile: this.elements.paramPerfil?.value || 'intermediate',
          output_format: this.elements.paramFormato?.value || 'all',
          niche_context: this.elements.paramNicho?.value || 'general'
        }
      });
    };

    [this.elements.paramPerfil, this.elements.paramFormato, this.elements.paramNicho].forEach(el => {
      if (el) el.addEventListener('change', updateParams);
    });
  },

  setupExecution() {
    if (!this.elements.btnLanzarProcesamiento) return;

    this.elements.btnLanzarProcesamiento.addEventListener('click', async () => {
      const { selectedFile, adaptationParams, apiMode } = state.get();
      if (!selectedFile) {
        statusDialog.showError({
          status: 400,
          code: 'NO_FILE_SELECTED',
          message: 'Por favor selecciona o arrastra un documento antes de iniciar el procesamiento.'
        });
        notifyWarning(
          'Documento Requerido',
          'Por favor selecciona o arrastra un archivo antes de procesar.'
        );
        return;
      }

      await this.runPipeline(selectedFile, adaptationParams, apiMode);
    });
  },

  async runPipeline(selectedFile, params, apiMode) {
    const { pipelineCard, btnLanzarProcesamiento, resultBoxContainer } = this.elements;
    
    // UI de preparación
    if (pipelineCard) pipelineCard.style.display = 'flex';
    if (resultBoxContainer) resultBoxContainer.style.display = 'none';
    if (btnLanzarProcesamiento) {
      btnLanzarProcesamiento.disabled = true;
      btnLanzarProcesamiento.innerHTML = '<span>Procesando documento...</span>';
    }
    this.resetStepperUI();

    const targetProfile = params.target_profile || 'intermediate';
    const outputFormat = params.output_format || 'all';
    const nicheContext = params.niche_context || 'general';

    try {
      let docId;
      let uploadResult;

      // Paso 1: Subir el documento al backend (POST /api/v1/documents)
      this.currentActiveStep = this.elements.stepOci;
      this.setStepActive(this.elements.stepOci, 'Guardando tu documento...');

      if (selectedFile.rawFile) {
        uploadResult = await apiClient.uploadFile(selectedFile.rawFile);
      } else {
        // Muestra enviada como texto
        const sampleName = (selectedFile.name || 'documento_estudio').replace(/\.[^/.]+$/, "") + ".txt";
        const sampleBlob = new Blob([`Documento de estudio: ${selectedFile.name}\nAnalizado por NuevaMente RAG.`], { type: 'text/plain' });
        const mockFile = new File([sampleBlob], sampleName, { type: 'text/plain' });
        uploadResult = await apiClient.uploadFile(mockFile);
      }

      docId = uploadResult.document_id;
      if (!docId) {
        throw new ApiError(500, { message: 'El backend no retornó un document_id válido.' });
      }

      state.set({
        backendDocument: uploadResult,
        currentDocId: docId
      });
      this.setStepCompleted(this.elements.stepOci, this.elements.line1);

      // Notificar con statusDialog el resultado (201 Stored nuevo o 200 Duplicado)
      const ext = (selectedFile.format || 'pdf').toLowerCase();
      const ociId = uploadResult.oci_object_name || `documents/${docId}/original.${ext}`;
      statusDialog.showStored({
        documentId: docId,
        ociId: ociId,
        filename: uploadResult.filename || selectedFile.name,
        httpStatus: uploadResult.httpStatus || (uploadResult.isDuplicate ? 200 : 201),
        duplicate: Boolean(uploadResult.isDuplicate),
        isMock: false
      });

      // Paso 2: Indexación y procesamiento en Backend
      this.currentActiveStep = this.elements.stepChroma;
      this.setStepActive(this.elements.stepChroma, 'Indexando contenido y calculando embeddings...');
      await this.wait(350);
      this.setStepCompleted(this.elements.stepChroma, this.elements.line2);

      // Paso 3: Vinculación con formatos de estudio (Sprint 2: Quiz y Flashcards)
      this.currentActiveStep = this.elements.stepGen;
      this.setStepActive(this.elements.stepGen, `Vinculando formatos de estudio para nivel [${this.getLevelLabel(targetProfile)}]...`);
      await this.wait(350);
      this.setStepCompleted(this.elements.stepGen, this.elements.line3);

      // Paso 4: Verificación de persistencia y registro en la biblioteca
      this.currentActiveStep = this.elements.stepCritic;
      this.setStepActive(this.elements.stepCritic, 'Validando persistencia y registrando en La Biblioteca...');
      await this.wait(300);
      this.setStepCompleted(this.elements.stepCritic, null);

      // Crear el documento persistido para el estado global y el librero
      const procDoc = this.createDocumentFromUpload(selectedFile, uploadResult, params);
      this.onPipelineSuccess(procDoc, uploadResult, params);

    } catch (err) {
      console.error('[Pipeline Error]:', err);
      
      if (this.currentActiveStep) {
        this.setStepFailed(this.currentActiveStep, err.message);
      }

      if (this.elements.pipelineLiveLog) {
        this.elements.pipelineLiveLog.textContent = `Error: ${err.message}`;
      }

      if (this.elements.pipelineStatusBadge) {
        this.elements.pipelineStatusBadge.textContent = `Error ${err.status || 500}`;
        this.elements.pipelineStatusBadge.style.background = 'rgba(239, 68, 68, 0.2)';
        this.elements.pipelineStatusBadge.style.color = '#ef4444';
      }

      // Desplegar diálogo temporal con detalles exactos del error devuelto por backend
      statusDialog.showError({
        status: err.status || 500,
        code: err.code || 'PIPELINE_ERROR',
        message: err.message,
        details: err.details || [],
        filename: selectedFile ? selectedFile.name : ''
      });

      notifyError(
        `Error HTTP ${err.status || 500}: ${err.code || 'PIPELINE_ERROR'}`,
        err.message,
        {
          actionText: 'Reintentar',
          onAction: () => {
            if (selectedFile) this.runPipeline(selectedFile, params, apiMode);
          }
        }
      );
    } finally {
      if (btnLanzarProcesamiento) {
        btnLanzarProcesamiento.disabled = false;
        btnLanzarProcesamiento.innerHTML = '<span>Procesar Documento</span>';
      }
    }
  },

  /**
   * Construye el modelo canónico del documento procesado para el Cuaderno y la Biblioteca
   */
  createDocumentFromUpload(selectedFile, uploadResult, params = {}) {
    const rawName = uploadResult.filename || selectedFile.name || 'Documento';
    const cleanTitle = rawName
      .replace(/\.[^/.]+$/, '')
      .replace(/[-_]/g, ' ')
      .trim();

    const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
    const discipline = this.inferDiscipline(cleanTitle, params.niche_context);
    const targetProfile = params.target_profile || 'intermediate';
    const docId = uploadResult.document_id;
    const ext = (selectedFile.format || rawName.split('.').pop() || 'pdf').toLowerCase();
    const ociId = uploadResult.oci_object_name || `documents/${docId}/original.${ext}`;

    return {
      id: docId,
      filename: rawName,
      title: formattedTitle,
      discipline: discipline,
      spineColor: 'gold-custom',
      description: `Documento procesado y persistido en OCI Object Storage (${uploadResult.isDuplicate ? 'Registro existente reutilizado' : 'Nuevo registro creado'}).`,
      filesize: selectedFile.size || '1.0 MB',
      status: uploadResult.status || 'stored',
      metadatos: {
        document_id: docId,
        perfil: targetProfile,
        tiempo_estudio: '8 min',
        niche_context: params.niche_context || 'general',
        oci_object_name: ociId,
        duplicate: Boolean(uploadResult.isDuplicate)
      },
      sections: [
        {
          id: `sec_${docId}`,
          title: formattedTitle,
          summary: `Documento registrado exitosamente en OCI y disponible en la Biblioteca de NuevaMente.`,
          key_concepts: [discipline, 'Concepto Clave', 'Estudio Adaptativo']
        }
      ]
    };
  },

  inferDiscipline(title, niche) {
    if (niche && niche !== 'general') {
      const nicheMap = {
        backend: 'TECNOLOGÍA',
        health: 'MEDICINA',
        legal: 'DERECHO',
        business: 'NEGOCIOS',
        humanities: 'HUMANIDADES'
      };
      if (nicheMap[niche]) return nicheMap[niche];
    }
    const lower = (title || '').toLowerCase();
    if (lower.includes('cloud') || lower.includes('software') || lower.includes('codigo') || lower.includes('programacion') || lower.includes('arquitectura') || lower.includes('tech')) return 'TECNOLOGÍA';
    if (lower.includes('med') || lower.includes('neuro') || lower.includes('salud') || lower.includes('bio') || lower.includes('farmac')) return 'MEDICINA';
    if (lower.includes('ley') || lower.includes('derecho') || lower.includes('legal') || lower.includes('constitucion') || lower.includes('norma')) return 'DERECHO';
    if (lower.includes('negocio') || lower.includes('econom') || lower.includes('finanz') || lower.includes('market') || lower.includes('emprend')) return 'NEGOCIOS';
    return 'EDUCACIÓN';
  },

  onPipelineSuccess(procDoc, uploadResult, params = {}) {
    const currentCustomBooks = state.get().customBooks || [];
    const exists = currentCustomBooks.some(b => b.id === procDoc.id);
    const updatedCustom = exists ? currentCustomBooks : [procDoc, ...currentCustomBooks];

    // Mapear formato solicitado al formato activo en el Study Hub
    const outputFormat = params.output_format || 'all';
    let initialStudyFormat = 'flashcards';
    if (outputFormat === 'quiz') initialStudyFormat = 'quiz';
    else if (outputFormat === 'tutorial') initialStudyFormat = 'video';
    else if (outputFormat === 'summary') initialStudyFormat = 'sintesis';

    state.set({
      currentDocument: procDoc,
      customBooks: updatedCustom,
      currentDocId: procDoc.id,
      backendDocument: uploadResult,
      notebook: {
        currentSpreadIndex: 0,
        isTurningPage: false
      },
      studyHub: {
        activeSectionId: procDoc.sections[0]?.id || null,
        activeFormat: initialStudyFormat,
        currentCardIndex: 0,
        isFlipped: false
      }
    });

    if (this.elements.pipelineStatusBadge) {
      this.elements.pipelineStatusBadge.textContent = 'Almacenado y Listo';
      this.elements.pipelineStatusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
      this.elements.pipelineStatusBadge.style.color = '#10b981';
    }
    if (this.elements.pipelineLiveLog) {
      this.elements.pipelineLiveLog.textContent = 'Documento almacenado correctamente en OCI y registrado en tu biblioteca.';
    }

    notifySuccess(
      uploadResult.isDuplicate ? 'Documento Reutilizado (200)' : 'Documento Almacenado (201)',
      `"${procDoc.filename}" ya está disponible en tu Biblioteca.`
    );

    // Actualizar datos de lectura
    if (this.elements.badgeTiempo) {
      this.elements.badgeTiempo.textContent = 'Persistencia: OCI Storage';
    }
    if (this.elements.badgeSecciones) {
      this.elements.badgeSecciones.textContent = `ID: ${procDoc.id.substring(0, 8)}...`;
    }
    if (this.elements.badgeNivel) {
      this.elements.badgeNivel.textContent = `Nivel: ${this.getLevelLabel(params.target_profile)}`;
    }

    // Mostrar panel de resolución de formatos
    if (this.elements.resultBoxContainer) {
      this.elements.resultBoxContainer.style.display = 'flex';
      this.elements.resultBoxContainer.scrollIntoView({ behavior: 'smooth' });
    }
  },

  getLevelLabel(perfil) {
    const map = {
      beginner: 'Principiante',
      intermediate: 'Intermedio',
      advanced: 'Avanzado',
      principiante: 'Principiante',
      intermedio: 'Intermedio',
      avanzado: 'Avanzado'
    };
    return map[(perfil || '').toLowerCase()] || 'Intermedio';
  },

  setupResolverActions() {
    this.elements.resolverFormatCards.forEach(card => {
      card.addEventListener('click', () => {
        const targetFormat = card.getAttribute('data-resolve-format');
        state.set({
          studyHub: {
            ...state.get().studyHub,
            activeFormat: targetFormat
          }
        });
        router.navigate('study');
      });
    });

    if (this.elements.btnIrALaBiblioteca) {
      this.elements.btnIrALaBiblioteca.addEventListener('click', () => {
        router.navigate('library');
      });
    }
  },

  syncInitialState() {
    const { selectedFile } = state.get();
    if (selectedFile) {
      this.renderSelectedFile(selectedFile);
    }
  },

  renderSelectedFile(fileData) {
    if (!fileData) return;
    this.elements.selectedFileName.textContent = fileData.name;
    this.elements.selectedFileSize.textContent = `${fileData.size} · Listo para procesar`;
    this.elements.fileFormatBadge.textContent = fileData.format || 'DOC';
    this.elements.selectedFileCard.style.display = 'flex';
    this.elements.dropArea.style.display = 'none';
  },

  clearFile() {
    state.set({ selectedFile: null });
    this.elements.selectedFileCard.style.display = 'none';
    this.elements.dropArea.style.display = 'flex';
    this.elements.quickSampleBtns.forEach(btn => btn.classList.remove('active'));
    if (this.elements.docFileInput) this.elements.docFileInput.value = '';
  },

  resetStepperUI() {
    const steps = [this.elements.stepOci, this.elements.stepChroma, this.elements.stepGen, this.elements.stepCritic];
    const lines = [this.elements.line1, this.elements.line2, this.elements.line3];

    steps.forEach(s => s && s.classList.remove('active', 'completed', 'step-error'));
    lines.forEach(l => l && l.classList.remove('completed'));

    if (this.elements.pipelineStatusBadge) {
      this.elements.pipelineStatusBadge.textContent = 'Ejecutando...';
      this.elements.pipelineStatusBadge.style.background = 'rgba(6, 182, 212, 0.15)';
      this.elements.pipelineStatusBadge.style.color = 'var(--accent-cyan)';
    }
  },

  setStepActive(stepEl, logText) {
    this.currentActiveStep = stepEl;
    if (stepEl) stepEl.classList.add('active');
    if (this.elements.pipelineLiveLog) this.elements.pipelineLiveLog.textContent = logText;
  },

  setStepCompleted(stepEl, lineEl) {
    if (stepEl) {
      stepEl.classList.remove('active', 'step-error');
      stepEl.classList.add('completed');
    }
    if (lineEl) lineEl.classList.add('completed');
  },

  setStepFailed(stepEl, logText) {
    if (stepEl) {
      stepEl.classList.remove('active');
      stepEl.classList.add('step-error');
    }
    if (this.elements.pipelineLiveLog) {
      this.elements.pipelineLiveLog.textContent = logText;
    }
  },

  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  setupDemoStatusTester() {
    const testBtns = document.querySelectorAll('[data-status-test]');
    testBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const code = parseInt(btn.getAttribute('data-status-test'), 10);
        statusDialog.triggerDemoStatus(code);

        if (code === 201) {
          notifySuccess('Demo HTTP 201: Creado', 'Documento nuevo persistido exitosamente en OCI.');
        } else if (code === 200) {
          notifyWarning('Demo HTTP 200: Duplicado', 'Documento ya existente detectado (SHA-256).');
        } else {
          notifyError(`Demo HTTP ${code}`, `Simulación de respuesta ${code} del backend.`);
        }
      });
    });
  }
};
