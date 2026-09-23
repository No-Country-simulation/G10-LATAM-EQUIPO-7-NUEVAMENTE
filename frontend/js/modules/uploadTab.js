/**
 * uploadTab.js
 * Controlador de la Pestaña Completa de Ingesta, Parámetros Pedagógicos y Pipeline RAG.
 */

import { state } from '../state.js';
import { sampleLibrary } from '../data/sampleLibrary.js';
import { mockService } from '../api/mockService.js';
import { apiClient } from '../api/apiClient.js';
import { router } from './router.js';

export const uploadTab = {
  elements: {},

  init() {
    this.bindElements();
    this.setupDropzone();
    this.setupSampleButtons();
    this.setupParamListeners();
    this.setupExecution();
    this.setupResolverActions();
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
      paramDetalle: document.getElementById('paramDetalle'),

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

  handleFileChosen(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    const allowed = ['pdf', 'md', 'txt'];
    if (!allowed.includes(ext)) {
      alert(`Formato de archivo no soportado (.${ext}). Solo se admiten archivos PDF, Markdown (.md) y TXT.`);
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
          if (sample.metadatos.perfil && this.elements.paramPerfil) {
            this.elements.paramPerfil.value = sample.metadatos.perfil;
          }
          if (sample.metadatos.nivel_detalle && this.elements.paramDetalle) {
            this.elements.paramDetalle.value = sample.metadatos.nivel_detalle;
          }
        }
      });
    });
  },

  setupParamListeners() {
    const updateParams = () => {
      state.set({
        adaptationParams: {
          perfil: this.elements.paramPerfil?.value || 'intermedio',
          formato: this.elements.paramFormato?.value || 'todos',
          nicho: this.elements.paramNicho?.value || 'auto',
          detalle: this.elements.paramDetalle?.value || 'equilibrado'
        }
      });
    };

    [this.elements.paramPerfil, this.elements.paramFormato, this.elements.paramNicho, this.elements.paramDetalle].forEach(el => {
      if (el) el.addEventListener('change', updateParams);
    });
  },

  setupExecution() {
    if (!this.elements.btnLanzarProcesamiento) return;

    this.elements.btnLanzarProcesamiento.addEventListener('click', async () => {
      const { selectedFile, adaptationParams, apiMode } = state.get();
      if (!selectedFile) {
        alert('Por favor selecciona o arrastra un documento para procesar.');
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

    try {
      if (apiMode === 'real' && selectedFile.rawFile) {
        // Modo Real: Envía el archivo al backend FastAPI (POST /api/v1/documents)
        this.setStepActive(this.elements.stepOci, 'Subiendo archivo al backend FastAPI (POST /api/v1/documents)...');
        const uploadResult = await apiClient.uploadFile(selectedFile.rawFile);
        console.log('[Backend API /documents] Respuesta recibida:', uploadResult);

        // Guardar metadatos del documento (soporta tanto document_id como filename/original_filename)
        const docId = uploadResult.document_id || uploadResult.filename || selectedFile.name;
        state.set({
          backendDocument: uploadResult,
          currentDocId: docId
        });
        this.setStepCompleted(this.elements.stepOci, this.elements.line1);

        this.setStepActive(this.elements.stepChroma, 'Indexando chunks en vector store...');
        await this.wait(600);
        this.setStepCompleted(this.elements.stepChroma, this.elements.line2);

        this.setStepActive(this.elements.stepGen, 'Agente Generador procesando consultas...');
        await this.wait(700);
        this.setStepCompleted(this.elements.stepGen, this.elements.line3);

        this.setStepActive(this.elements.stepCritic, 'Agente Crítico validando coherencia conceptual...');
        await this.wait(500);
        this.setStepCompleted(this.elements.stepCritic, null);

        // Procesar resultado estructurado
        const { document: procDoc, structuredJson } = await mockService.processMockPipeline(selectedFile, params);
        this.onPipelineSuccess(procDoc, structuredJson);
      } else {
        // Modo Mock (o muestra sin rawFile)
        this.setStepActive(this.elements.stepOci, 'Almacenando documento en OCI Object Storage...');
        await this.wait(550);
        this.setStepCompleted(this.elements.stepOci, this.elements.line1);

        this.setStepActive(this.elements.stepChroma, 'ChromaDB: particionando documento y calculando embeddings...');
        await this.wait(700);
        this.setStepCompleted(this.elements.stepChroma, this.elements.line2);

        this.setStepActive(this.elements.stepGen, `Agente Generador: Extrayendo conceptos para perfil [${params.perfil}]...`);
        await this.wait(800);
        this.setStepCompleted(this.elements.stepGen, this.elements.line3);

        this.setStepActive(this.elements.stepCritic, 'Agente Revisor: Evaluando fidelidad conceptual (99.2%) y estructura JSON...');
        await this.wait(600);
        this.setStepCompleted(this.elements.stepCritic, null);

        const { document: procDoc, structuredJson } = await mockService.processMockPipeline(selectedFile, params);
        this.onPipelineSuccess(procDoc, structuredJson);
      }
    } catch (err) {
      console.error('[Pipeline Error]:', err);
      if (this.elements.pipelineLiveLog) this.elements.pipelineLiveLog.textContent = `Error: ${err.message}`;
      if (this.elements.pipelineStatusBadge) {
        this.elements.pipelineStatusBadge.textContent = 'Fallo';
        this.elements.pipelineStatusBadge.style.background = 'rgba(239, 68, 68, 0.2)';
        this.elements.pipelineStatusBadge.style.color = '#ef4444';
      }
      alert(`No se pudo completar el procesamiento: ${err.message}`);
    } finally {
      if (btnLanzarProcesamiento) {
        btnLanzarProcesamiento.disabled = false;
        btnLanzarProcesamiento.innerHTML = '<span>Procesar Documento</span>';
      }
    }
  },

  onPipelineSuccess(procDoc, structuredJson) {
    const currentCustomBooks = state.get().customBooks || [];
    const exists = currentCustomBooks.some(b => b.id === procDoc.id);
    const updatedCustom = exists ? currentCustomBooks : [procDoc, ...currentCustomBooks];

    state.set({
      currentDocument: procDoc,
      customBooks: updatedCustom,
      lastStructuredJson: structuredJson,
      notebook: {
        currentSpreadIndex: 0,
        isTurningPage: false
      },
      studyHub: {
        activeSectionId: procDoc.sections[0]?.id || null,
        activeFormat: 'flashcards',
        currentCardIndex: 0,
        isFlipped: false
      }
    });

    if (this.elements.pipelineStatusBadge) {
      this.elements.pipelineStatusBadge.textContent = 'Completado';
      this.elements.pipelineStatusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
      this.elements.pipelineStatusBadge.style.color = '#10b981';
    }
    if (this.elements.pipelineLiveLog) {
      this.elements.pipelineLiveLog.textContent = 'Documento procesado correctamente. Ya está disponible en tu biblioteca.';
    }

    // Actualizar datos de estudio
    const meta = structuredJson.metadatos || {};
    if (this.elements.badgeTiempo) {
      this.elements.badgeTiempo.textContent = `Tiempo de lectura: ${meta.tiempo_estudio || '8 min'}`;
    }
    if (this.elements.badgeSecciones) {
      this.elements.badgeSecciones.textContent = `Secciones: ${procDoc.sections?.length || 1}`;
    }
    if (this.elements.badgeNivel) {
      this.elements.badgeNivel.textContent = `Nivel: ${this.getLevelLabel(meta.perfil)}`;
    }

    // Mostrar panel de resolución de formatos
    if (this.elements.resultBoxContainer) {
      this.elements.resultBoxContainer.style.display = 'flex';
      this.elements.resultBoxContainer.scrollIntoView({ behavior: 'smooth' });
    }
  },

  getLevelLabel(perfil) {
    const map = {
      principiante: 'Principiante',
      intermedio: 'Intermedio',
      avanzado: 'Avanzado'
    };
    return map[(perfil || '').toLowerCase()] || 'General';
  },

  setupResolverActions() {
    // Tarjetas del resolver (Flashcards, Quiz, Video, Resumen)
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

    // Botón para ir a la biblioteca
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
    this.elements.selectedFileSize.textContent = `${fileData.size} · Listo para indexación`;
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

    steps.forEach(s => s && s.classList.remove('active', 'completed'));
    lines.forEach(l => l && l.classList.remove('completed'));

    if (this.elements.pipelineStatusBadge) {
      this.elements.pipelineStatusBadge.textContent = 'Ejecutando...';
      this.elements.pipelineStatusBadge.style.background = 'rgba(6, 182, 212, 0.15)';
      this.elements.pipelineStatusBadge.style.color = 'var(--accent-cyan)';
    }
  },

  setStepActive(stepEl, logText) {
    if (stepEl) stepEl.classList.add('active');
    if (this.elements.pipelineLiveLog) this.elements.pipelineLiveLog.textContent = logText;
  },

  setStepCompleted(stepEl, lineEl) {
    if (stepEl) {
      stepEl.classList.remove('active');
      stepEl.classList.add('completed');
    }
    if (lineEl) lineEl.classList.add('completed');
  },

  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
};
